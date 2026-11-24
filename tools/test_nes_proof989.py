"""Exercise late WRAM damage and credit-ordered writes on an identical 910 prefix."""
import argparse
from pathlib import Path

from unittest.mock import patch
import nes_proof989 as proof
from nes_proof989 import PACKED, PROOF, ROM, TABLE, observer
from nes_scroll989 import ROM as SCROLL
from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw506 import once

FAULTS = ("scroll","table","length","append","stop","bad_seal")


def fixed(t, phase, fault=None, scroll=False):
    base = directory(t,phase,"985after","cold")
    cmds,_ = packet_path(base,911)
    old=(PACKED/"body.bin").read_bytes()
    new=((SCROLL if scroll else ROM)/"body.bin").read_bytes()
    changes=[f"emu.write({0x2000+i},{b},emu.memType.snesWorkRam)"
             for i,b in enumerate(new) if i>=len(old) or old[i]!=b]
    out=t/f"nes-{'scroll989' if scroll else 'proof989'}-fixed-p{phase}-{'stoplatched' if fault=='stop' else fault or 'normal'}"
    if fault=="append":
        gen,op,clock,wire,bulk,obs,elapsed=cmds[-1]
        assert gen==911 and op==3
        seal=bytearray.fromhex(wire)
        packet=bytearray(seal[:16])
        packet[:2]=bytes((2,5))
        packet[10:16]=bytes.fromhex("1a0602000000")
        seal[2]+=1
        cmds[-1]=(gen,2,clock,(packet+b'\0\0').hex(),bulk,obs,elapsed)
        cmds.append((gen,3,clock+15000,seal.hex(),bulk,obs+15000,elapsed))

    if fault=="overlap":
        g,_,at,wire,bulk,obs,duration=cmds[-1]
        packet=bytearray.fromhex(wire)[:16]
        packet[:2]=bytes((2,5));packet[10:16]=bytes((0,0,2,0,0,0))
        cmds[-1]=(g,2,at,(packet+bytes((127,169))).hex(),bulk,obs,duration)

    def observe(lua):
        with patch.object(proof,"ROM",SCROLL if scroll else ROM):
            lua=observer(lua)
        at='packet=requests[index];sample516'
        edit="if pw(8)==911 and pb(0)==1 then\n"+"\n".join(changes)+"\nend"
        if fault in ("scroll","table","length"):
            addr={"scroll":0x6501,"table":TABLE+81+19,"length":TABLE+248}[fault]
            edit+=f"""
 if pw(8)==911 and pb(0)==3 then
  assert(word({PROOF})==1,'missing checked range')
  local a=0x10000+word(0x1020)+{addr}
  emu.write(a,rd(a)~1,emu.memType.snesWorkRam)
 end"""
        if fault=="append":
            edit+=f"""
 if pw(8)==911 and pb(0)==2 and pw(10)==1562 then assert(word({PROOF})==1) end
 if pw(8)==911 and pb(0)==3 then assert(word({PROOF})==0) end"""
        if fault=="overlap":
            edit+=f"\n if pw(8)==911 and pb(0)==2 and pw(2)==15 then assert(word({PROOF})==1) end"
        if fault=="stop":
            edit+=f"\n if pw(8)==911 and pb(0)==3 then assert(word({PROOF})==1) end"
            lua=once(lua,"if MODE=='stop_decode'and decodeStart then return 128 end",
                     "if MODE=='stop_decode' then return 128 end")
        if fault:
            lua=once(lua,"if rejected then\n   local screen",
                     f"if rejected then\n   assert(word({PROOF})==0,'live proof after abort')\n   local screen")
        return once(lua,at,'packet=requests[index]\n'+edit+'\n sample516')

    mode="stop_decode" if fault=="stop" else fault
    return replay(t,base,out,"fixed",cmds,911,mode,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("fault",choices=(*FAULTS,"overlap"),nargs="?")
    p.add_argument("--scroll",action="store_true")
    a=p.parse_args()
    fixed(a.temp,a.phase,a.fault,a.scroll)
