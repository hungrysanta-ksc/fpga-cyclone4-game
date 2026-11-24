"""Measure the seal's executed CPU cycles and fixed-path identity, and screen neighboring frames."""
import argparse
from pathlib import Path

from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw506 import once

TAPS="""
local sig999,n999=0,0
local hits999={}
local function tag999(name)
 local s=emu.getState()
 local f=assert(io.open(ROOT..'/cost999.txt','a'))
 f:write(name,' ',s.masterClock,' ',assert(s['cpu.cycleCount']),' ',n999,' ',sig999,'\\n')
 f:close()
 if name=='validated' or name=='upload' then
  local hits=assert(io.open(ROOT..'/'..name..'999-hits.txt','w'))
  for pc,n in pairs(hits999) do hits:write(pc,' ',n,'\\n') end
  hits:close()
 end
end
checkedMem527(function()
 if packet and pw(8)==907 and pb(0)==3 then
  checkedMem527(function(pc)
  if pc==0x7e264e then tag999('seal') end
  if pc==0x7e2fb2 then tag999('validate') end
  if pc==0x7e26e1 then tag999('validated') end
  if pc==0x7e2a7e then tag999('upload') end
  sig999=((sig999*31)+pc)&0xffffffff
  n999=n999+1
  hits999[pc]=(hits999[pc] or 0)+1
  end,emu.callbackType.exec,0x7e2000,0x7e3fff)
  tag999('begin')
 end
end,emu.callbackType.exec,0x7e264e,0x7e264e)
"""


def measure(temp,phase,mode):
    from replay_nes_ready999 import run
    def instrument(lua):
        anchor = "checkedMem527(function()sample516('upload165_entry')end,emu.callbackType.exec,8268414)"
        return once(lua,anchor,anchor+"\n"+TAPS)
    run(temp,phase,True,mode,instrumentation=instrument,suffix="-audit")


def screen(t,p,g,mode):
    d=directory(t,p,"978returned","cold")
    op=[r["packet_opcode"] for r in read(d/"events.json") if r["generation"]==g and r.get("opcode")=="0xe1"]
    commands,_=packet_path(d,g,expected_shape=(len(op),op.count(7)))
    # Fixed actual tile availability. Keep boot/preceding frames and BEGIN.
    # All ordinary packets are optimistically available, charged actual E1 time.
    def observe(s):
        return once(s,"if sent-retired>=4 then break end","if sent-retired>=2 then break end")
    replay(t,d,t/f"nes-ready999-screen-{g}-{mode}-p{p}",mode,commands,g,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("instant","busy","frame","prelude"))
    p.add_argument("--screen",type=int,choices=(909,910,912))
    a=p.parse_args()
    if a.screen:screen(a.temp,a.phase,a.screen,a.mode)
    else:measure(a.temp,a.phase,a.mode)
