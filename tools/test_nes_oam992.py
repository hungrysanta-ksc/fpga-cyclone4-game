"""Inject STOP during the 336B OAM fill and reject an overlong OAM repeat."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, read, replay
from nes_oam992 import ROOT
from nes_raw506 import once


def guard(temp,phase,fault):
    folder=directory(temp,phase,"992store","cold")
    packets,_=packet_path(folder,911)
    index=next(i for i,(g,op,*_) in enumerate(packets) if g==911 and op==8)
    packets=packets[:index+1]
    g,op,at,wire,bulk,observed,duration=packets[-1]
    b=bytearray.fromhex(wire)
    assert int.from_bytes(b[10:12],"little")==176 and int.from_bytes(b[14:16],"little")==336
    if fault=="span":
        b[14:16]=(384).to_bytes(2,"little")
        packets[-1]=(g,op,at,b.hex(),bulk,observed,duration)
    def observe(s):
        addr=read(ROOT/"store"/"labels.json")["write992"]
        s=once(s,"local function loaded()",f"""local writes992=0
checkedMem527(function()
 if packet and pw(8)==911 and pb(0)==8 then writes992=writes992+1 end
end,emu.callbackType.exec,{addr})
local function loaded()""")
        if fault=="stop":
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if writes992>=1 then return 128 end")
        return once(s,"if rejected then\n   local screen",
                    f"if rejected then\n   assert(writes992=={1 if fault=='stop' else 0},'accepted groups '..writes992)\n   local screen")
    return replay(temp,folder,temp/f"nes-oam992-guard-{fault}-p{phase}","fixed",packets,911,
                  "stop_decode" if fault=="stop" else "span",observe=observe)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("phase",type=int,choices=(1,2))
    parser.add_argument("fault",choices=("stop","span"))
    a=parser.parse_args();guard(a.temp,a.phase,a.fault)
