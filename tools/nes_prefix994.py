"""Pin boot and the 910 prefix, then substitute measured code or ideal color restoration."""
import argparse
import subprocess
from pathlib import Path
from unittest.mock import patch

import nes_page963
import nes_proof989
from nes_color994 import ROOT, BASE, PACKED, observe, once


def script(s,mode):
    if mode=="matched":
        with patch.object(nes_proof989,"ROM",ROOT/"both3"):
            s=nes_proof989.align_boot(s)
        s=observe(s,"both3")
        return once(s,"if packet and pb(1)==4 and (","if packet and pw(8)>=911 and pb(1)==4 and (")
    s=observe(s,"ref")
    s=once(s,"local function uniform545()", """local ideal994=false
local function uniform545()
 if ideal994 then return false end""")
    s=once(s,'sample516("load");reads=0','''ideal994=pw(8)==911 and ((pb(1)==3 and pw(10)>=128) or pb(1)==4)
 local op=ideal994 and {0x4c,0xce,0x25} or {0x8d,0x81,0x21}
 for i=1,3 do emu.write(0x2517+i,op[i],emu.memType.snesWorkRam) end
 sample516("load");reads=0''')
    return once(s,"local function loaded()", """checkedMem527(function()
 if not ideal994 then return end
 local sec=pb(1);local kind=pb(0);local pos=pw(10)
 local n=kind==2 and pw(12) or pw(14)
 local ptr=word(0x1020)+(sec==3 and 0x6000 or 0x6200)+pos
 assert(word(0x1034)~=word(0x1032) and emu.getState()['cpu.a']==ptr and word(0x1080+sec*2)==pos+n)
 assert(kind==2 or kind==4 or kind==8)
 for i=0,n-1 do
  local k=kind==2 and i or (i%(kind==4 and 2 or 4))
  emu.write(0x10000+ptr+i,pb(16+k),emu.memType.snesWorkRam)
 end
 sample516('instant994',n)
end,emu.callbackType.exec,0x7e2518)
local function loaded()""")


def run(temp,p,mode):
    original=subprocess.Popen
    def launch(cmd,*args,**kw):
        if "--testRunner" in cmd:
            f=Path(cmd[cmd.index("--testRunner")+1]);f.write_text(script(f.read_text(encoding="utf8"),mode),encoding="utf8",newline="\n")
        return original(cmd,*args,**kw)
    with patch.object(subprocess,"Popen",launch),patch.object(nes_page963,"PACKED",PACKED):
        nes_page963.simulate(temp,p,"cold",True,BASE,True,tag="994"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2));p.add_argument("mode",choices=("matched","ideal"))
    a=p.parse_args();run(a.temp,a.phase,a.mode)
