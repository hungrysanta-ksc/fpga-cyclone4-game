# SPDX-License-Identifier: MIT
"""Linked502/506 M4 reconstruction/planner/serializer equivalence. Isolated time."""
import argparse,json,re,struct
from pathlib import Path
from check_nes_game478 import Machine,encode as old_encode,sha
from audit_nes_output489 import CompactAudit
from nes_raw506 import encode

def check(a):
    a.out.mkdir(parents=True,exist_ok=False)
    pal=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.base/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
    machines=[]
    for name,path in [('base',a.base),('candidate',a.arm)]:
        d=a.out/name;d.mkdir();machines.append(CompactAudit(path,pal,d))
    reference=json.loads((a.reference/'result.json').read_text());rows=[]
    for serial,g in enumerate(range(905,a.last+1),1):
        files=[a.data/f'frame{g}.{e}'for e in ['geometry','raw']]
        for f in files:assert sha(f)==reference['input_sha256'][f.name]
        geom,raw=[f.read_bytes()for f in files];result=[]
        for m,enc in zip(machines,[old_encode,encode]):
            packets,_,_=enc(geom,raw,g);r=m.frame(packets,geom,raw,g,serial)
            (m.out/f'frame{g}/plans.json').write_text(json.dumps(r['plans'])+'\n')
            result.append(dict(receive_instructions=r['receive_instructions'],planner_instructions=r['planner_instructions'],packets=len(packets),payload_B=sum(map(len,packets)),minimum_source_wire_B=sum(map(len,packets))+19*len(packets)+8,canonical_SHA256=m.canonical_state_SHA256,serializer_instructions=m.rows[-1]['target_instructions']))
        states=[]
        for m in machines:
            q=m.layout['nes_native165'];b=bytearray(m.u.mem_read(m.state,q['size']))
            # Packet token/status CRC legitimately differ with packet count;
            #all semantic/coverage/error/history bytes must remain identical.
            for key,n in [('next_token',2),('status183',8)]:b[q[key]:q[key]+n]=bytes(n)
            states.append(bytes(b)+bytes(m.u.mem_read(m.video,m.layout['nes_native_video165']['size']))+bytes(m.u.mem_read(m.resident,m.layout['nes_resident211']['size'])))
        assert states[0]==states[1],g
        assert machines[0].plans==machines[1].plans and machines[0].packets==machines[1].packets
        rows.append(dict(generation=g,raw_B=len(raw),baseline=result[0],candidate=result[1]))
        print(json.dumps(rows[-1]),flush=True)
    guards=[]
    for label,n,start,gen,upper,ok in [('run10',10,0,9,0,True),('run256',256,0,9,0,True),('short9',9,0,9,0,False),('zero',0,0,9,0,False),('long257',257,0,9,0,False),('hole',10,1,9,0,False),('stale',10,0,8,0,False),('reserved',10,0,9,1<<20,False)]:
        m=Machine(a.arm,pal);layout=m.layout['nes_native165']
        for key,value,size in [('state',1,1),('generation',9,2),('next_kind',7,1),('patch_count',1,1),('last_tile',0,2)]:m.u.mem_write(m.state+layout[key],value.to_bytes(size,'little'))
        q=struct.pack('>HHQ',0xf000+start,gen,upper|(n<<6)|63)
        m.packets=[q,b''];m.index=0;m.prepared=False;m.start_token=0;m.spi_calls=0
        got=m.call('nes_native165_poll',[m.state,m.spi|1,0]);assert bool(got)==ok,(label,got,m.state_value())
        b=bytes(m.u.mem_read(m.state+layout['raw_pixels'],256))
        assert b==(bytes([63])*n+bytes(256-n)if ok else bytes(256)),label
        guards.append(dict(name=label,accepted=ok))
    report=dict(passed=True,scope=__doc__,baseline_firmware=sha(a.base/'obj-nes-100/firmware.stm'),candidate_firmware=sha(a.arm/'obj-nes-100/firmware.stm'),rows=rows,guards=guards,actual_common_clock=False,new_installer=False)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['base','arm','data','reference','out']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--last',type=int,default=916);check(p.parse_args())
