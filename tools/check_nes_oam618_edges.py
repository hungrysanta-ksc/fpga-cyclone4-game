# SPDX-License-Identifier: MIT
"""Pace one already checked SEAL descriptor against the real late VBlank beam."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def test(a,line,interrupt=False):
    labels=json.loads((a.client/'labels.json').read_text())
    trial=f'checked-{line}'+('-stop' if interrupt else '')
    def fixture(source):
        lua=r"""
local chosen618,stop618,latched618=false,false,false
local n618,first618,last618=0,0,0
local function put618(a,bytes)
 for i,v in ipairs(bytes) do emu.write(a+i-1,v,emu.memType.snesWorkRam) end
end
local function beam618()
 local st=emu.getState()
 return st['ppu.scanline'],st['memoryManager.hClock'] or st['ppu.hClock']
end
emu.addMemoryCallback(function()
 if not packet or pb(0)~=3 or pw(8)~=FAULT or chosen618 then return end
 -- Test-only pacing stubs replay the original LDX cursor and latch read.
 assert(rd(@GROUP@)==0xae and word(@GROUP@+1)==0x1252)
 assert(rd(@SAMPLE@)==0xad and word(@SAMPLE@+1)==0x2137)
 put618(@GROUP@,{0x20,0,0x36})
 put618(@SAMPLE@,{0x20,0x20,0x36})
 put618(0x3600,{0x08,0xe2,0x20,0x48,0xad,0x5e,0x60,0xf0,0xfb,0x68,0x28,0xae,0x52,0x12,0x60})
 put618(0x3620,{0x48,0xad,0x5f,0x60,0xf0,0xfb,0x68,0xad,0x37,0x21,0x60})
end,emu.callbackType.exec,@UPLOAD@)
emu.addMemoryCallback(function()
 if chosen618 then return end
 local i=word(0x1252)
 while i<word(0x1250) do
  local d=word(0x4002+i);local len=word(0x4004+i)
  if d~=0x5000 and d~=0x9000 and len>=384 then
   -- Select a bounded prefix of an admitted normal job. STOP before reveal.
   put618(0x1252,{i%256,i//256});put618(0x4004+i,{128,1});chosen618=true;return
  end
  i=i+8
 end
 error('no checked descriptor large enough for edge fixture')
end,emu.callbackType.exec,0x7e3600)
emu.addMemoryCallback(function()
 local line=beam618();return (stop618 or line==248) and 1 or 0
end,emu.callbackType.read,0x605e)
emu.addMemoryCallback(function()
 local line,h=beam618();return (line==@LINE@ and h>=1090) and 1 or 0
end,emu.callbackType.read,0x605f)
emu.addMemoryCallback(function()
 if chosen618 and not latched618 then
  local line,h=beam618()
  assert(line==@LINE@ and h>=1090)
  latched618=emu.getState().masterClock
  if @INTERRUPT@ then stop618=true end
  local f=assert(io.open(ROOT..'/sample.txt','w'));f:write(line,',',h);f:close()
 end
end,emu.callbackType.exec,0x7e3627)
emu.addMemoryCallback(function()
 if chosen618 and latched618 and @LINE@==253 then stop618=true end
end,emu.callbackType.exec,@FRESH@)
"""
        lua=lua.replace('@GROUP@',str(labels['group538']&65535)).replace('@SAMPLE@',str(labels['sample618']&65535))
        lua=lua.replace('@UPLOAD@',str(labels['upload165_entry'])).replace('@FRESH@',str(labels['fresh8_618'])).replace('@LINE@',str(line))
        lua=lua.replace('@INTERRUPT@','true' if interrupt else 'false')
        s=once(source,'local function loaded()',lua+'\nlocal function loaded()')
        s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end","if stop618 then return 128 end")
        s=once(s,'if visible then\n   assert(dmaRemaining',"""if latched618 then
   assert(not stop618 and dmaLength==384)
   local l=beam618();if n618==0 then first618=l end
   n618=n618+1;last618=l;if n618==384 then stop618=true end
  end
  if visible then
   assert(dmaRemaining""")
        marker="assert(lastStatus==0xe4,'STOP status')"
        return once(s,marker,marker+f""";assert(latched618 and stop618 and n618=={384 if line==252 and not interrupt else 0})
  local f=assert(io.open(ROOT..'/edge.txt','w'));f:write(n618,',',first618,',',last618);f:close()""")
    result=exercise(a,906,trial,edit_packet_case=fixture)
    folder=a.out/f'906-{trial}'
    n,start,end=map(int,(folder/'edge.txt').read_text().split(','))
    y,h=map(int,(folder/'sample.txt').read_text().split(','))
    assert y==line and (not n or line<=start<=end<262)
    return dict(**result,line=y,h=h,B=n,start_line=start,end_line=end)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('client','trace','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    rows=[test(a,252),test(a,253),test(a,252,True)]
    (a.out/'edges.json').write_text(json.dumps(rows,indent=2)+'\n')
