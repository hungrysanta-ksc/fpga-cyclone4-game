# SPDX-License-Identifier: MIT
"""Observe the actual idle selector at 910/951 without changing arrivals or the running 65816."""
import argparse
from pathlib import Path
from nes_raw506 import once
import replay_nes_map527 as replay
from test_nes_map526_schedule import observer
from test_nes_tile532 import tile_observer


def instrument(s, labels):
    s=tile_observer(observer(s,labels),labels)
    hooks=["local probes=assert(io.open(ROOT..'/selector536.csv','w'))",
           "probes:write('g,event,clock,line,frame,index,head,tail,x,n,head_src,head_B,tail_src,tail_B\\n')",
           """local function probe536(event)
 local g=word(0x1226)
 if g~=910 and g~=951 then return end
 local st=emu.getState(); local l=st['ppu.scanline']
 if l<225 or l>255 then return end
 local h=word(0x1252);local t=word(0x1250)
 local function field(i,delta)
  if i<h or i>=t then return -1 end
  return word(0x4000+i+delta)
 end
 probes:write(string.format('%d,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',g,event,st.masterClock,l,st.frameCount,index,h,t,st['cpu.x'],st['cpu.y'],field(h,0),field(h,4),field(t-8,0),field(t-8,4)))
end"""]
    for name in ('prefix523','empty526','selected526','defer_beam','priority524','skip8_523','grant524'):
        hooks.append(f"emu.addMemoryCallback(function()probe536('{name}')end,emu.callbackType.exec,{labels[name]})")
    return once(s,'local function loaded()','\n'.join(hooks)+'\nlocal function loaded()')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.frames=53
    replay.observer=instrument
    replay.run(a)
