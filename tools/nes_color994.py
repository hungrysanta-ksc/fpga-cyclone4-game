"""Replay the unchanged 978 ARM with receiver-stage timing and checked OAM fills."""
import argparse
import subprocess
from pathlib import Path
from unittest.mock import patch

import nes_page963
from nes_hdma990 import BASE, PACKED
from nes_raw506 import once

ROOT=BASE.parent/"nes-color994"


def observe(s,mode):
    # After select920 returns the checked destination address, $2518 opens
    # the WRAM port. At accepted the complete logical range has been copied.
    extra=[]
    owners=[]
    if mode in ("scatter3","both3"):
        owners.append("(pb(0)==8 and pw(12)==4 and pb(16)==pb(18) and pb(16)==pb(19))")
    if mode in ("uniform3","both3"):
        owners.append("(pb(0)==4 and pw(12)==2 and pb(16)==pb(17))")
    if owners:
        s=once(s,"local function uniform545()", "local function uniform545()\n if packet and pb(1)==4 and ("+" or ".join(owners)+") then return true end")
        s=once(s,"pb(1)==5 and 0x6500 or 0x6000","pb(1)==5 and 0x6500 or pb(1)==4 and 0x6200 or 0x6000")
        s=once(s,"rd(address+j)==pb(16)","rd(address+j)==pb(pb(0)==8 and 16+j%4 or 16)")
        s=once(s,"if uniform545() then\n   assert(fillBytes545","if uniform545() and (pb(1)~=4 or ack[1]<224) then\n   assert(fillBytes545")
    for name,pc in (("checked",0x2518),("accepted",0x275a),("identity",0x2222),
                    ("data",0x24be),("service_in",0x3619),("service_out",0x3667)):
        extra.append(f"""checkedMem527(function()
 if packet and pw(8)==911 and (pb(1)==3 or pb(1)==4) then
  sample516('color994_{name}')
 end
end,emu.callbackType.exec,{0x7e0000+pc})""")
    return once(s,"local function loaded()","\n".join(extra)+"\nlocal function loaded()")


def run(t,p,mode):
    from nes_overlap993 import ROOT as arm993
    arm=arm993/"split" if mode=="split" else BASE
    receiver="both3" if mode=="split" else mode
    source=PACKED if receiver=="ref" else ROOT/receiver
    popen=subprocess.Popen
    def instrument(cmd,*args,**kw):
        if "--testRunner" in cmd:
            file=Path(cmd[cmd.index("--testRunner")+1])
            file.write_text(observe(file.read_text(encoding="utf8"),receiver),encoding="utf8",newline="\n")
        return popen(cmd,*args,**kw)
    with patch.object(nes_page963,"PACKED",source),patch.object(subprocess,"Popen",instrument):
        nes_page963.simulate(t,p,"cold",True,arm,True,tag="994"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2));p.add_argument("mode")
    a=p.parse_args();run(a.temp,a.phase,a.mode)
