"""Charge each diagnostic SPI page on the linked ARM/65816 replay. ROM stamps
are exercised in the board bench. The ARM fixture uses cache hits for all tiles.
"""
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch
from replay_nes_tile903 import joint, replay, window, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_PC
from prepare_nes_supply905 import WORK
from read_nes_supply905 import decode,SIZE

def run(temp,clip,phase,*,tag='905-supply',out=None,base=None,runner=replay,work=WORK,edition=905):
    out=out or temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}'
    base=base or temp/f'nes-tile821-{clip}-jointmirror-p{phase}-903-tile'
    original=joint.Runtime.__init__
    holders=[];pages=[]
    def stamp(t):return int(t*84000000/joint.MASTER/32768)&1023
    def init(cpu,args,link):
        original(cpu,args,link);holders.append(cpu)
        returns={}
        exch=link.exchange
        def observe(*a):
            lines=exch(*a)
            for item in (lines[3] if len(lines)>3 else '').split(';'):
                if item:
                    tok,t=map(int,item.split(':'));returns[tok]=t
            return lines
        link.exchange=observe
        def frame(u,*_):
            if cpu.generation>=907:u.reg_write(UC_ARM_REG_R0,(5500 if clip=='late' else 3000)+cpu.generation-907)
        def query(u,*_):
            tx=u.reg_read(UC_ARM_REG_R1)
            if u.mem_read(tx,1)!=b'\x78':return
            assert clip=='late' and u.reg_read(UC_ARM_REG_R3)==32 and 0x20000000<=tx<0x20010000
            page=u.mem_read(tx+1,1)[0];g=cpu.generation
            jobs=[j for j in map(json.loads,(out/'producer.jsonl').read_text().splitlines()) if j['generation']==g]
            t0=next(e['start'] for e in cpu.events if e.get('opcode')=='0xe9' and e['generation']==g)
            last=jobs[-1]; count=sum(j['bytes']//(16<<j['kind']) for j in jobs)
            tt=cpu.clock+8*joint.MASTER/2625000
            h=struct.pack('<BBHBBHHHI',0,0x95,g,count,len(jobs),stamp(t0),stamp(tt),stamp(last['producer']),last['token'])
            body=bytearray(16)
            if page>=128:
                for i,j in enumerate(jobs[2*(page-128):2*(page-128)+2]):
                    tok=j['token']
                    v=(tok%2048)<<21|((tok-1)%2)<<20|j['kind']<<19|(j['bytes']//16)<<11|stamp(returns[tok])
                    struct.pack_into('<I',body,8*i,v)
            pages.append((g,page))
            u.mem_write(u.reg_read(UC_ARM_REG_R2),h+bytes(body))
            cpu.clock+=32*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        for name,fn in [('nes_budget210_frame',frame),('nes_native165_bulk',query)]:
            at=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,fn,begin=at,end=at)
    with patch.object(joint.Runtime,'__init__',init):
        runner(temp,temp/'nes-latency898',897,clip,phase,candidate_arm=work/'link/src',replay_tag=tag)
    cpu,=holders
    path=out/'records.bin';path.write_bytes(cpu.u.mem_read(cpu.data_symbols['ptrcache'],SIZE+2*(edition==907)))
    data=decode(path,edition)
    assert len(data['rows'])==(6 if clip=='late' else 0) and not any(data['dropped'])
    assert all('invalid' not in r for r in data['rows'])
    if clip=='late':assert any(r.get('detail') for r in data['rows'])
    def marks(p):
        w={r['g']:r for r in window(p) if r['event']=='reveal'}
        return w[912]['frame']-w[906]['frame']
    for g in range(905,913):assert (out/f'frame-{g}.rgb').read_bytes()==(base/f'frame-{g}.rgb').read_bytes()
    result=dict(pages=len(pages),selected=data['selected'],RGB=8,intervals=[marks(base),marks(out)],
                final_ACK=[json.loads((p/'joint.json').read_bytes())['frames'][-1]['ACK_masterclock'] for p in (base,out)])
    (out/'verified905.json').write_text(json.dumps(result))
    print(result)
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2],int(sys.argv[3]))
