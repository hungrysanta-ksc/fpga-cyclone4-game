"""Replay the complete linked path or price only the remaining 911 receiver work."""
import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
import nes_page963
from build_nes_oam996 import WORK, ROM
from nes_raw506 import once


def ideal(s,rom):
    labels=json.loads((rom/"labels.json").read_bytes())
    verify=labels["verify996"] & 65535
    done=labels["done996"] & 65535
    # A diagnostic only: at the checked range, verify and restore in zero
    # simulated cycles. Credits, other packets, SPI and PPU still execute.
    code=f"""local instant996=false
checkedMem527(function()
 if not instant996 then return end
 local base=0x10000+word(0x1020)+0x6200
 local cut=pw(20)
 assert(pw(10)<=cut and cut<=512 and word(0x1088)==544)
 for i=cut,543 do
  local expected=(i<512 and i%4==1) and 240 or 0
  assert(rd(base+i)==expected)
 end
 for i=pw(10),cut-1 do emu.write(base+i,i%4==1 and 240 or 0,emu.memType.snesWorkRam) end
 sample516('instant996',cut-pw(10))
end,emu.callbackType.exec,{0x7e0000+verify})
local function loaded()"""
    s=once(s,"local function loaded()",code)
    return once(s,'sample516("load");reads=0',f"""instant996=pw(8)==911 and pb(0)==8 and pw(12)==6
 local op=instant996 and {{0x4c,{done&255},{done>>8}}} or {{0x20,0x19,0x36}}
 for i,b in ipairs(op) do emu.write({verify}-1+i,b,emu.memType.snesWorkRam) end
 sample516("load");reads=0""")


def run(t,p,mode):
    rom=WORK/"grouped" if mode in ("grouped","groupwire") else ROM
    popen=subprocess.Popen
    def launch(cmd,*args,**kwargs):
        if mode in ("ideal","idealwire") and "--testRunner" in cmd:
            f=Path(cmd[cmd.index("--testRunner")+1]);f.write_text(ideal(f.read_text(encoding="utf8"),rom),encoding="utf8",newline="\n")
        return popen(cmd,*args,**kwargs)
    with patch.object(nes_page963,"PACKED",rom),patch.object(subprocess,"Popen",launch):
        if mode.endswith("wire"):
            from nes_sparse995 import run as wire_schedule
            wire_schedule(t,p,"all3",work=WORK,tag="996"+mode)
        else:
            nes_page963.simulate(t,p,"cold",True,WORK,True,tag="996"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("tail","grouped","ideal","groupwire","idealwire"),nargs="?",default="tail")
    a=p.parse_args();run(a.temp,a.phase,a.mode)
