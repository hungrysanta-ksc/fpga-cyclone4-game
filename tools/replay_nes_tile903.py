"""Run the actual final ARM and 65816 with a modeled 26-byte trace reply."""
import argparse
import json
import struct
from pathlib import Path
from unittest.mock import patch

from compare_nes_latency898 import joint,replay
from analyze_nes_map830 import window
from prepare_nes_tile903 import WORK
from read_nes_tile903 import ROW,decode
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC


def run(temp,clip,phase):
    tag='903-tile'
    out=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}'
    baseline=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-frame901'
    original=joint.Runtime.__init__
    holders=[]
    def init(cpu,args,link):
        original(cpu,args,link)
        holders.append(cpu)
        def frame(u,*_):
            if cpu.generation>=907:
                u.reg_write(UC_ARM_REG_R0,(5500 if clip=='late' else 3000)+cpu.generation-907)
        def query(u,*_):
            if u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]!=0x78:return
            assert clip=='late' and u.reg_read(UC_ARM_REG_R3)==26
            g=cpu.generation
            w=window(out)
            def last(kind,g,op=None):
                return [r for r in w if r['g']==g and r['event']==kind and (op is None or r['op']==op)][-1]['clock']
            jobs=[v for v in map(json.loads,(out/'producer.jsonl').read_text().splitlines()) if v['generation']==g]
            j=jobs[-1]
            polls=[e for e in cpu.events if e.get('opcode')=='0xe8' and (rx:=bytes.fromhex(e['reply']))[6] and
                   int.from_bytes(rx[14:18],'little')==j['token']]
            e8=polls[0]['start']+8*joint.MASTER/2625000
            issued=[e for e in cpu.events if e.get('packet_opcode')==7 and e['generation']==g][-1]
            heads=[r for r in w if r['g']==g and r['event']=='ack' and r['op']==7]
            # The consumer observes the prior receipt after the hardware pop.
            # Use readiness as the lower bound on visibility in this timing replay.
            stamps=[last('reveal',g-1),j['producer'],j['producer'],e8,issued['start']+16*joint.MASTER/2625000,
                    last('load',g,7),last('reveal',g),cpu.clock+8*joint.MASTER/2625000]
            assert heads and stamps[1:] == sorted(stamps[1:])
            wire=struct.pack('<BBB H 8H I B',0,0x93,7,g,*[int(v*84000000/joint.MASTER/512)&65535 for v in stamps],j['token'],j['kind'])
            u.mem_write(u.reg_read(UC_ARM_REG_R2),wire)
            cpu.clock+=26*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        for name,fn in [('nes_budget210_frame',frame),('nes_native165_bulk',query)]:
            pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
    with patch.object(joint.Runtime,'__init__',init):
        replay(temp,temp/'nes-latency898',897,clip,phase,candidate_arm=WORK/'link/src',replay_tag=tag)
    cpu,=holders
    addr=cpu.data_symbols['ptrcache']
    count=int.from_bytes(cpu.u.mem_read(addr+6,2),'little')
    assert count==(6 if clip=='late' else 0),count
    path=out/'records.bin'
    path.write_bytes(cpu.u.mem_read(addr,16+ROW.size*count))
    trace=decode(path)
    assert not any(trace['dropped']) and all('invalid' not in r and 'token' in r for r in trace['rows']),trace
    def marks(folder):
        return {r['g']:r for r in window(folder) if r['event']=='reveal'}
    current,base=marks(out),marks(baseline)
    for g in range(905,913):
        assert (out/f'frame-{g}.rgb').read_bytes()==(baseline/f'frame-{g}.rgb').read_bytes()
    for r in trace['rows']:
        g=r['generation'];assert r['VBlanks']==current[g]['frame']-current[g-1]['frame']
    result=dict(records=count,RGB=8,intervals=[v[912]['frame']-v[906]['frame'] for v in (base,current)],
                last_ACK_difference_clocks=json.loads((out/'joint.json').read_bytes())['frames'][-1]['ACK_masterclock']-
                json.loads((baseline/'joint.json').read_bytes())['frames'][-1]['ACK_masterclock'])
    (out/'verified903.json').write_text(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('temp',type=Path);p.add_argument('clip',choices=['early','late']);p.add_argument('phase',type=int,choices=[1,2])
    a=p.parse_args();run(a.temp,a.clip,a.phase)
