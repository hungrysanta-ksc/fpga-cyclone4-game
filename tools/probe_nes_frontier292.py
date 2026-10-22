# SPDX-License-Identifier: MIT
"""Trace actual retained M4 planner frontiers; no timing/ACK/RTL replacement."""
import argparse
import binascii
import csv
import json
import struct
from pathlib import Path

from probe_nes_native289 import Producer
from probe_nes_arm264 import plans
from probe_nes_decode280 import records, chunks
from nes_delta231 import BASE, sha


def decode(data):
    result=[];at=0
    while at<len(data):
        assert len(data)-at>=3
        size,count=struct.unpack_from('<HB',data,at);at+=3;end=at+size
        assert 0<count<=15 and end<=len(data)
        for _ in range(count):
            op=data[at];kind=op&3;short=bool(op&128)
            assert kind<=2 and (op<=130 if short else op<=2)
            n=({0:7,1:8,2:3}[kind] if short else 16+2*data[at+1].bit_count())
            assert at+n<=end
            pos=3 if short else 4
            slot=0 if kind==2 else int.from_bytes(data[at+pos:at+pos+2],'little')
            result.append((int(kind==1),slot,32 if kind==1 else 16))
            at+=n
        assert at==end
    return result


def ranges(items,final=False):
    closed=[];current=None
    for kind,slot,n in items:
        if current and (kind!=current[0] or slot!=current[1]+current[2]//n or current[2]+n>2048):
            closed.append(current);current=None
        if current is None:current=[kind,slot,0]
        current[2]+=n
    if final and current:closed.append(current)
    return closed,current


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);ap.add_argument('--last',type=int,default=975)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    elf=a.source/'output.elf';arm=Producer(elf,None);pins={str(elf):sha(elf)}
    for name in ('reset259','reset285','reset280'):arm.call(name,[])
    palette=BASE/'probes/nes-delta231/test07/palette.bin';pins[str(palette)]=sha(palette)
    arm.uc.mem_write(arm.symbols['palette285'],palette.read_bytes())
    arm.uc.mem_write(0x20010000,b'\xa5'*32768)
    word=lambda n:struct.unpack('<I',arm.uc.mem_read(arm.symbols[n],4))[0]
    memory=lambda n,length:bytes(arm.uc.mem_read(arm.symbols[n],length))
    _,groups=plans();rows=[];steps=[]
    normalize=lambda p:p[:16]+b'\0'*4 if p[0]==7 else p
    for f in range(905,a.last+1):
        src=BASE/f'probes/nes-joint284/test04/frame{f}.records';pins[str(src)]=sha(src)
        for b in chunks(records(src)):
            arm.uc.mem_write(0x20028000,b)
            assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        components={}
        for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):
            before=arm.instructions;assert arm.call(name,[]);components[name]=arm.instructions-before
        initial=memory('batch285',word('batch_size285'))
        assert word('batch_count285')==1 and len(initial)==3 and initial[0]==0x82
        assert word('output_size285')==0
        first=[];previous=b'';planner_start=arm.instructions
        for step in range(34):
            before=arm.instructions;ok=arm.call('next_step286',[]);assert ok
            immutable=memory('output285',word('output_size285'))
            assert immutable.startswith(previous);previous=immutable
            pending=memory('batch285',word('batch_size285'));count=word('batch_count285')
            emitted=decode(immutable)
            speculative=decode(struct.pack('<HB',len(pending),count)+pending) if count else []
            assert len(emitted)+len(speculative)==word('calls285')
            closed,current=ranges(emitted)
            # This hypothetical freeze is not wire-compatible: insertion sort
            # can still change pending order and aperture closure needs a next plan.
            hypothetical,_=ranges(emitted+speculative)
            row=dict(frame=f,step=step,result=ok,instructions=arm.instructions-before,
                     since_step_start=arm.instructions-planner_start,
                     immutable_bytes=len(immutable),immutable_plans=len(emitted),
                     pending_bytes=len(pending),pending_plans=count,
                     closed_ranges=len(closed),hypothetical_freeze_closed=len(hypothetical),
                     open_range_bytes=current[2] if current else 0,
                     pending_hex=pending.hex(),closed_detail=json.dumps(closed),
                     hypothetical_detail=json.dumps(hypothetical))
            steps.append(row);first.append(row)
            if ok==2:break
        else:raise AssertionError('unbounded planner')
        oracle=BASE/f'probes/nes-joint284/test04/plans{f-904}.bin';pins[str(oracle)]=sha(oracle)
        assert immutable==oracle.read_bytes() and not pending
        final,_=ranges(emitted,True)
        at=len(arm.packets);before=arm.instructions
        assert arm.call('prepare289',[]) and arm.call('produce289',[])
        produced=arm.packets[at:]
        assert list(map(normalize,produced))==list(map(normalize,groups[f-904]))
        actual=[[p[1],int.from_bytes(p[10:12],'little')//(32 if p[1] else 16),int.from_bytes(p[14:16],'little')] for p in produced if p[0]==7]
        assert final==actual,(f,final,actual)
        producer_cost=arm.instructions-before
        assert arm.call('commit285',[])
        first_step=lambda key:next((x['step'] for x in first if x[key]),None)
        early=[x for x in first if x['result']!=2]
        row=dict(frame=f,components=components,steps=len(first),plans=len(emitted),ranges=len(final),
                 initial_pending_hex=initial.hex(),first_pending=-1,first_immutable=first_step('immutable_plans'),
                 first_closed=first_step('closed_ranges'),final_step=step,
                 early_closed=max((x['closed_ranges'] for x in early),default=0),
                 early_hypothetical_closed=max((x['hypothetical_freeze_closed'] for x in early),default=0),
                 planner_steps_instructions=sum(x['instructions'] for x in first),
                 producer_instructions=producer_cost,fixture_reads=arm.fixture_reads)
        rows.append(row);print(json.dumps(row),flush=True)
    assert not arm.fixture_reads
    with (a.out/'steps.csv').open('w',newline='',encoding='utf-8') as fp:
        w=csv.DictWriter(fp,fieldnames=list(steps[0]),lineterminator='\n');w.writeheader();w.writerows(steps)
    result=dict(passed=True,stage=292,frames=rows,input_hashes=pins,
                script_sha256=sha(Path(__file__)),fixture_reads=0,actual_ACK=False,
                new_ELF=False,new_RTL=False,new_schedule=False,scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
