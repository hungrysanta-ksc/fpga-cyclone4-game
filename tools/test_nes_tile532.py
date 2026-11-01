# SPDX-License-Identifier: MIT
"""Check the actual accepted tile payload and every early VRAM write on the joint timeline."""
import argparse
import json
from pathlib import Path
import test_nes_raw506_joint as joint
from trace_nes_output531 import OutputRuntime,instrument
from trace_nes_map527 import CheckedLink,run_schedule
from nes_raw506 import once
import replay_nes_map527 as replay
from test_nes_map526_schedule import observer


def tile_observer(s,labels,map_limit='128'):
    if 'normal_length532' in labels:
        s=once(s,'assert(n==64 and off%64==0 and accepted526[off] and not copied526[off])',
               f'''assert(n>=64 and n%64==0 and n<={map_limit} and off%64==0)
  for j=off,off+n-1,64 do assert(accepted526[j] and not copied526[j])end''')
        s=once(s,'word(0x4004+i)>=64',f'n==math.min({map_limit},word(0x4004+i))')
        s=once(s,'pending526={off=off','pending526={n=n,off=off')
        s=once(s,'for j=0,63 do','for j=0,p.n-1 do')
        s=once(s,'copied526[p.off]=true','for j=p.off,p.off+p.n-1,64 do copied526[j]=true end')
    s=once(s,'local pending526=nil',r"""local pending526=nil
local bytes532={}
local tile532=nil
local f532=assert(io.open(ROOT..'/tile532.csv','w'));f532:write('g,event,clock,src,dst,n,other\n')
local function log532(name,src,dst,n,other)
 f532:write(string.format('%d,%s,%d,%d,%d,%d,%d\n',word(0x1226),name,emu.getState().masterClock,src,dst,n,other))
 f532:flush()
end""")
    s=once(s,'then accepted526={};copied526={} end','''then accepted526={};copied526={};bytes532={} end
  if pb(0)==7 and lastStatus==0 then
   local bank=word(0x1034)
   local dst=(pb(1)==0 and (bank==0 and 0 or 0xc000) or (bank==0 and 0x4000 or 0x8000))+pw(10)
   assert(#tile==pw(14))
   for j=1,#tile do assert(bytes532[dst+j-1]==nil);bytes532[dst+j-1]=tile:byte(j) end
  end''')
    s=once(s,'assert(i<tail and src==word(0x4000+i)', '''assert(not tile532 and i<=tail and (i<tail or n<=160))
  for j=0,n-1 do assert(bytes532[dst+j]~=nil,'tile not accepted') end
  tile532={dst=dst,n=n}
  log532('tile',src,dst,n,i==tail and 1 or 0)
  assert(src==word(0x4000+i)''')
    s=once(s,' if pending526 then',''' if tile532 then
  local t=tile532
  for j=0,t.n-1 do assert(emu.read(t.dst+j,emu.memType.snesVideoRam)==bytes532[t.dst+j],'early tile VRAM');bytes532[t.dst+j]=nil end
  tile532=nil
 end
 if pending526 then''')
    register='checkedMem527' if 'local function checkedMem527' in s else 'emu.addMemoryCallback'
    if 'scan532' in labels:
        s=once(s,'assert(not tile532 and i<=tail and (i<tail or n<=160))',
               '''local head=i;i=emu.getState()['cpu.x']
  assert(not tile532 and i>=head and i<=tail and (i-head)%8==0 and (i==head or n<=160))''')
        s=once(s,"n,i==tail and 1 or 0)","n,i==tail and 1 or (i~=head and 2 or 0))")
    return once(s,'local function loaded()',f"""{register}(verify526(function()
 local x=emu.getState()['cpu.x'];local tail=word(0x1250)-8
 if x<tail then
  assert(x==tail-8 and x>=word(0x1252) and (word(0x4000+tail)&0x7000)==0x5000)
  assert(word(0x4000+x)+word(0x4004+x)==word(0x70) and word(0x4002+x)+word(0x4004+x)==word(0x72))
  log532('merge',word(0x70),word(0x72),word(0x74),word(0x4004+x))
 end
end),emu.callbackType.exec,{labels['merge_written532']})
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture','trace'):
        p.add_argument('--'+n,type=Path,required=n in ('client','mesen','out'))
    p.add_argument('--start-clock',type=int)
    p.add_argument('--trace-credit',action='store_true')
    p.add_argument('--trace-rom',action='store_true')
    a=p.parse_args();a.map526=True;joint.Runtime=OutputRuntime
    limit=json.loads((a.client/'build.json').read_text())['map_chunk_B']
    assert limit in (64,128,256)
    if a.trace:
        a.frames=53
        replay.observer=lambda s,l:tile_observer(observer(s,l),l,str(limit))
        replay.run(a)
    else:
        labels=json.loads((a.client/'labels.json').read_text())
        run_schedule(a,lambda s,args:tile_observer(instrument(s,args),labels,str(limit)),CheckedLink,frames=53)
