"""Exercise the production ARM recorder and 65816 using the two matched MMC898 clips."""
import argparse
import json
import struct
from unittest.mock import patch
from pathlib import Path

from compare_nes_latency898 import replay,joint
from analyze_nes_map830 import window
from prepare_nes_frame900 import PARENTS,WORK
from read_nes_frame900 import read_trace
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR


def run(temp,n,clip,phase,control):
    parent=PARENTS[n][0]
    tag=f'frame{n}'+('-control-boot' if control else '')
    out=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}'
    base=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-898-{parent}'
    original=joint.Runtime.__init__
    original_call=joint.Runtime.call
    def call(cpu,name,args):
        if name=='nes_runtime165_begin':
            cpu.u.mem_write(cpu.data_symbols['mode900'],bytes([3 if control else 0]))
        return original_call(cpu,name,args)
    holders=[]
    def init(cpu,args,link):
        original(cpu,args,link)
        holders.append(cpu)
        def hook(name,func):
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,func,begin=pc,end=pc)
        def frame(u,*_):
            if cpu.generation>=907:
                u.reg_write(UC_ARM_REG_R0,(3000 if clip=='early' else 5500)+cpu.generation-907)
        hook('nes_budget210_frame',frame)
        def query(u,*_):
            tx=u.reg_read(UC_ARM_REG_R1)
            if u.mem_read(tx,1)[0]!=0x78:return
            assert not control and 0x20000000<=tx<0x20010000 and u.reg_read(UC_ARM_REG_R3)==26
            g=cpu.generation
            all_rows=window(out)
            w=[r for r in all_rows if r['g']==g]
            def pick(event,predicate):
                return [r['clock'] for r in w if r['event']==event and predicate(r)]
            maps=lambda r:r['section']==2
            tiles=lambda r:r['op']==7
            stamps=[pick('load',maps),pick('load',tiles),pick('seal',lambda r:True),pick('ppu_last',lambda r:True),
                    pick('reveal',lambda r:True),pick('ack',lambda r:r['op']==3),
                    [r['clock'] for r in all_rows if r['g']==g-1 and r['event']=='reveal'],
                    pick('ack',maps),pick('ack',tiles),[cpu.clock+8*joint.MASTER/2625000]]
            wire=bytearray(26)
            wire[1:5]=bytes((0x90,sum(1<<i for i,j in enumerate((0,1,2,3,4,5,7,8)) if stamps[j]),
                              g&255,g>>8))
            for i,values in enumerate(stamps):
                struct.pack_into('<H',wire,5+2*i,int(values[-1]*84000000/joint.MASTER/512)&65535 if values else 0)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(wire))
            cpu.clock+=26*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        hook('nes_native165_bulk',query)
    with patch.object(joint.Runtime,'__init__',init),patch.object(joint.Runtime,'call',call):
        replay(temp,temp/'nes-latency898',parent,clip,phase,candidate_arm=WORK/f'link{n}/src',replay_tag=tag)
    cpu,=holders
    addr=cpu.data_symbols['ptrcache']
    header=bytes(cpu.u.mem_read(addr,16))
    count=struct.unpack_from('<H',header,6)[0]
    assert count==6,(count,header.hex())
    path=out/'records.bin'
    path.write_bytes(header+bytes(cpu.u.mem_read(addr+16,42*count)))
    trace=read_trace(path)
    assert trace['dropped']==[0,0] and all('invalid' not in r for r in trace['rows']),trace
    def shows(folder):
        return {r['g']:r['frame'] for r in window(folder) if r['event']=='reveal'}
    v=shows(out);old=shows(base)
    for r in trace['rows']:
        g=r['generation']
        if not control:assert r['VBlanks']==v[g]-v[g-1]
        assert (out/f'frame-{g}.rgb').read_bytes()==(base/f'frame-{g}.rgb').read_bytes()
    (out/'verified900.json').write_text(json.dumps(dict(count=count,RGB=6,intervals=v[912]-v[906],
                  reference=old[912]-old[906],query='modeled wire and fixed driver overhead',control=control)))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('temp',type=Path);p.add_argument('edition',type=int,choices=PARENTS)
    p.add_argument('clip',choices=('early','late'));p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('--control',action='store_true')
    a=p.parse_args();run(a.temp,a.edition,a.clip,a.phase,a.control)
