# SPDX-License-Identifier: MIT
"""Actual canonical expansion, early H2 and cooperative group-step M4 probe.

Original compressed records and all independent output bytes are preserved.
The forced geometry block boundary is a separately charged packing candidate;
neither mode implements speculative FPGA execution or a live full firmware.
"""
import argparse,binascii,csv,json,shutil,struct,subprocess,inspect
from pathlib import Path
import probe_nes_planner285 as prior
from nes_planner286 import patch
from nes_delta231 import BASE,ROOT,sha,once
from probe_nes_decode280 import records,chunks,golden


def build(d):
    source=inspect.getsource(prior.build)
    anchor="    (d/'stubs.s').write_text"
    at=source.index(anchor)
    source=source[:at]+'''    p=d/'nes_planner211.c';p.write_text(patch(p.read_text()),encoding='utf-8',newline='\\n')
    p=d/'nes_planner285.c';s=p.read_text();start=s.index('unsigned plan285(');end=s.index('unsigned commit285(',start)
    s=s[:start]+s[end:];s+='\\n#include "nes_input286.inc"\\n'
    p.write_text(s,encoding='utf-8',newline='\\n')
    for n in ('nes_input286.inc','nes_decode280.c'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[str(ROOT/'tools'/n)]=sha(ROOT/'tools'/n)
    pins[str(ROOT/'tools/nes_planner286.py')]=sha(ROOT/'tools/nes_planner286.py')
'''+source[at:]
    source=source.replace('-u,plan285,','-u,block286,-u,geometry_ready286,-u,expand286,-u,geometry_plan286,-u,h2early286,-u,input_commit286,-u,begin_step286,-u,next_step286,-u,stop286,-u,reset280,-u,context_size286,')
    ns=dict(prior.__dict__);ns['patch']=patch;exec(compile(source,'build286','exec'),ns);return ns['build'](d)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--last',type=int,default=975);ap.add_argument('--geometry-boundary',action='store_true');a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins=build(d)
    arm=prior.Planner(d/'planner.elf',None);arm.call('reset285',[]);arm.call('reset280',[])
    p=BASE/'probes/nes-delta231/test07/palette.bin';pins[str(p)]=sha(p);arm.uc.mem_write(arm.symbols['palette285'],p.read_bytes())
    layout=[arm.call('layout285',[i]) for i in range(7)];rows=[];guards=[]
    for f in range(905,a.last+1):
        path=BASE/f'probes/nes-joint284/test04/frame{f}.records';pins[str(path)]=sha(path);rr=records(path)
        split=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\x00\x03')+1
        bb=chunks(rr[:split])+chunks(rr[split:]) if a.geometry_boundary else chunks(rr)
        costs={};at_events=len(arm.events);decoder=0;preview_at=None
        def call(name,args=[]):
            before=arm.instructions;r=arm.call(name,args);return r,arm.instructions-before
        for i,b in enumerate(bb):
            arm.uc.mem_write(0x20028000,b);ok,n=call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)]);assert ok;decoder+=n
            if preview_at is None and arm.call('geometry_ready286',[]):
                for name in ('expand286','begin285','geometry_plan286','h2early286'):
                    ok,n=call(name);assert ok,(f,name,arm.word('expansion_error286'));costs[name]=n
                preview_at=i;assert arm.word('calls285')==0
                cert=bytes(arm.uc.mem_read(arm.symbols['certificate286'],32))
                p=BASE/f'probes/nes-joint284/test04/prelude{f}.hex';pins[str(p)]=sha(p)
                assert cert==bytes.fromhex(p.read_text())[16:48],('H2',f,cert.hex())
                if f in (905,907,954):
                    saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save()
                    assert arm.call('begin_step286',[])==0 and arm.word('calls285')==0
                    arm.call('stop286',[]);assert arm.call('next_step286',[])==0 and arm.call('input_commit286',[])==0
                    guards.append(dict(frame=f,phase='geometry',early_start_rejected=True,STOP_rejected=True))
                    arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx)
        geom,raw=golden(f);assert bytes(arm.uc.mem_read(arm.symbols['history286'],4910))==geom+raw
        for name in ('input_commit286','begin_step286'):
            ok,n=call(name);assert ok,(f,name);costs[name]=n
        steps=[]
        while True:
            ok,n=call('next_step286');assert ok,(f,len(steps));steps.append(n)
            if ok==2:break
            assert len(steps)<=32
            if len(steps)==1 and f in (905,907,954):
                saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save();before_calls=arm.word('calls285')
                arm.call('stop286',[]);assert arm.call('next_step286',[])==0 and arm.word('calls285')==before_calls
                guards.append(dict(frame=f,phase='group',STOP_rejected=True));arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx)
        out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')))
        p=BASE/f'probes/nes-joint284/test04/plans{f-904}.bin';pins[str(p)]=sha(p);assert out==p.read_bytes(),('plan',f)
        p=BASE/f'probes/nes-wholepath247/jointdecode-test02/run/expected-{f-904}.bin';pins[str(p)]=sha(p);v=arm.symbols['video285'];meta=p.read_bytes()
        actual=bytes(arm.uc.mem_read(v+layout[0],4096))+bytes(arm.uc.mem_read(v+layout[1],512))+bytes(arm.uc.mem_read(v+layout[2],544))+bytes(arm.uc.mem_read(v+layout[1]+512,1121))+bytes(arm.uc.mem_read(v,2291))+bytes(arm.uc.mem_read(v+2292,6))
        assert actual==meta,('full metadata',f,next((i for i,(x,y) in enumerate(zip(actual,meta)) if x!=y),None))
        ok,commit=call('commit285');assert ok
        total=sum(costs.values())+sum(steps)
        row=dict(frame=f,components=costs,steps=steps,postdecode_instructions=total,postdecode_CPI1_ms=total/84000,commit_instructions=commit,decoder_instructions=decoder,
                 first_H2_block=preview_at,blocks=len(bb),old_blocks=len(chunks(rr)),extra_block_count=len(bb)-len(chunks(rr)),tail_payload=sum(map(len,bb[preview_at+1:])),plan_bytes=len(out),callbacks=arm.word('calls285'),max_group_instructions=max(steps[:-1]),final_step_instructions=steps[-1])
        rows.append(row);print(json.dumps(row),flush=True)
    result=dict(passed=True,stage=286,frames=rows,guards=guards,metadata_bytes_per_frame=8570,context_bytes=arm.call('context_size286',[]),certificate_bytes=32,
                size=(d/'size.log').read_text(),observed_stack=0x2003f000-arm.low_sp,geometry_boundary=a.geometry_boundary,input_hashes=pins,
                script_sha256=sha(Path(__file__)),generated_hashes={n:sha(d/n) for n in ('nes_planner211.c','nes_planner285.c','planner.elf')},
                limits=['Canonical decoder/expander and planner execute on actual M4 ELF; instruction counts, not hardware cycles.',
                        'Geometry H2 is speculative local data. No E9/ROM/output before full input commit; no new FPGA speculative lease.',
                        'Group-step callback still writes diagnostic buffers; IRQ preemption and bounded physical refill are not integrated.',
                        'The existing output ARM still recomputes H2 in the conservative retimed schedule; early H2 cost is additionally charged.'])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('passed','size','observed_stack','context_bytes')}))


if __name__=='__main__':main()
