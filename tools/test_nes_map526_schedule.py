# SPDX-License-Identifier: MIT
"""Assert that each early map write has an accepted producer and the expected pixels' map bytes."""
import argparse
from pathlib import Path
from nes_raw506 import once
from test_nes_idle524_schedule import observe
from test_nes_trim514_schedule import run_schedule
from trace_nes_obj518 import ObjLink


def observer(s,labels):
    s=once(s,' if a>=0x4300 and a<=0x4306 then regs[a]=v end',
           ' if a==0x2116 or a==0x2117 or (a>=0x4300 and a<=0x4306) then regs[a]=v end')
    s=once(s,'lastStatus=ack[1];sample516("ack",lastStatus)','''lastStatus=ack[1];sample516("ack",lastStatus)
  if pb(0)==1 and lastStatus==0 then accepted526={};copied526={} end
  if pb(1)==2 and lastStatus==0 and (pb(0)==2 or pb(0)==4) then
   local n=pb(0)==2 and pw(12) or pw(14)
   for offset=pw(10),pw(10)+n-1,64 do accepted526[offset]=true end
  end''')
    return once(s,'local function loaded()',f"""local accepted526,copied526={{}},{{}}
local pending526=nil
local function verify526(callback)
 return function(...)
  local ok,v=pcall(callback,...)
  if not ok then local f=assert(io.open(ROOT..'/map-error.txt','w'));f:write(tostring(v));f:close();emu.stop(1);return end
  return v
 end
end
emu.addMemoryCallback(verify526(function()
 local bank=word(0x1034);local src=regs[0x4302]+256*regs[0x4303]
 local dst=2*(regs[0x2116]+256*regs[0x2117]);local n=regs[0x4305]+256*regs[0x4306]
 local i=word(0x1252);local tail=word(0x1250)-8;local map=bank==0 and 0x6000 or 0xa000
 assert(not packet and not pending526 and bank~=word(0x1032) and word(0x1228)==1 and i<=tail)
 if dst>=map and dst<map+4096 then
  local off=dst-map;assert(n==64 and off%64==0 and accepted526[off] and not copied526[off])
  assert(src==word(0x1020)+0x5000+off)
  if word(0x4000+tail)==src then i=tail end
  assert(word(0x4000+i)==src and word(0x4002+i)==dst and word(0x4004+i)>=64)
  pending526={{off=off,dst=dst,g=word(0x1226)}}
  sample516('idle524',0x10000+off)
 else
  assert(i<tail and src==word(0x4000+i) and dst==word(0x4002+i) and n==word(0x4004+i) and n<=2048)
  sample516('idle524',i)
 end
end),emu.callbackType.exec,{labels['grant524']})
emu.addMemoryCallback(verify526(function()
 if pending526 then
  local p=pending526;local expected=file('map-'..p.g..'.bin')
  for j=0,63 do assert(emu.read(p.dst+j,emu.memType.snesVideoRam)==expected:byte(p.off+j+1),'early VRAM row') end
  copied526[p.off]=true;pending526=nil
 end
end),emu.callbackType.exec,{labels['retired526']})
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("arm","data","fixture","plans","client","mesen","out","calendar","driver503","capture"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--start-clock",type=int,required=True)
    run_schedule(p.parse_args(),lambda s,a:observe(s,a,observer),ObjLink,frames=53)
