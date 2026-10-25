# SPDX-License-Identifier: MIT
"""Execute new progress/credit/consume checks in the actual Cortex-M4 ELF."""
import argparse,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from nes_delta231 import sha

def crc(p):
    c=0
    for b in p:
        c^=b
        for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
    return c

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    arm=Producer(a.source/'output.elf',None);rows=[]
    def put(k,v,fmt='<I'):arm.uc.mem_write(arm.symbols[k],struct.pack(fmt,v))
    def check(name,sent=2,retired=0,accepted=2,released=2,issued=1,consumed=0,reported=1,tag=251,flags=0,badcrc=False,want=1,error=0):
        arm.call('reset259',[])
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired))
        put('issued312',issued,'<H');put('consumed312',consumed,'<H')
        p=bytearray([0,tag,flags,accepted>>8,accepted&255,released>>8,released&255,0,1,0,0,reported>>8,reported&255,0])
        p[-1]=crc(p[1:-1])^badcrc
        arm.uc.mem_write(0x20010000,bytes(p));got=arm.call('progress282',[0x20010000,len(p)])
        state=bytes(arm.uc.mem_read(arm.symbols['state259'],20))
        assert got==want,(name,got,state.hex())
        # state259 error has its stable ABI offset 17.
        assert state[17]==error,(name,state.hex(),error)
        rows.append(dict(name=name,accepted=bool(got),error=error))
    check('separate release and receipt')
    check('released but not yet consumed',reported=0)
    check('future consumed rejected',reported=2,want=0,error=23)
    check('regressing consumed rejected',consumed=1,reported=0,want=0,error=23)
    check('consume counter wrap',issued=0,consumed=65535,reported=0)
    check('storage counter wrap',sent=0,retired=65534,accepted=0,released=0)
    check('full two-slot status',released=0,flags=5,reported=0)
    check('third slot rejected',sent=3,accepted=3,released=0,flags=1,want=0,error=22)
    check('future storage release rejected',released=3,want=0,error=22)
    check('old version rejected',tag=250,want=0,error=21)
    check('CRC includes consumed bytes',badcrc=True,want=0,error=21)
    check('wrong full flag rejected',released=0,flags=1,want=0,error=22)
    arm.call('reset259',[]);put('plan_cache282',1)
    assert arm.call('progress282',[0x20010000,13])==1
    assert bytes(arm.uc.mem_read(arm.symbols['plan_cache282'],4))==b'\0'*4
    rows.append(dict(name='short E9 invalidates cached plan reply',accepted=True))
    for reason,sent,retired,phase,want in ((8,2,0,0,1),(8,1,0,0,0),(8,0,65534,0,1),(8,0,65535,0,0),(4,1,1,0,0),(4,1,0,0,1),(2,0,0,2,0)):
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired));put('phase_ready302',phase);put('wait_reason302',reason)
        assert arm.call('work_pending302',[])==want
        rows.append(dict(reason=reason,sent=sent,retired=retired,phase=phase,planner_allowed=want))
    r=dict(passed=True,checks=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),actual_SPI=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print('PASS312 ARM checks',len(rows))
if __name__=='__main__':main()
