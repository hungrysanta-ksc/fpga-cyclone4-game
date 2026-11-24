"""Observe actual semantic-check reads and empty queue polls without changing the ROM."""
import argparse
from pathlib import Path

from check_nes_plan975 import directory, packet_path, read, replay, sha
from nes_blank960 import PACKED
from nes_raw506 import once


def observer(lua):
    labels=read(PACKED/"labels.json")
    body="""local trace986=assert(io.open(ROOT..'/checks986.csv','w'))
trace986:write('event,clock,frame,line,h,index,offset,value\\n')
local phase986=''
local empty986=-1
local function mark986(event,off,value)
 local st=emu.getState()
 trace986:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d\\n',event,st.masterClock,st.frameCount,
   st['ppu.scanline'],st['memoryManager.hClock'],index,off or -1,value or -1))
 trace986:flush()
end
"""
    lua=once(lua,"local function sample516(event,value)",body+"local function sample516(event,value)")
    hooks=""
    for key in ("seal","validate181","scroll_end181","table181","table_end181","length181","coverage212","upload165_entry"):
        hooks+=f"""checkedMem527(function()
 if packet and pb(0)==3 and pw(8)==911 then phase986='{key}';mark986(phase986) end
end,emu.callbackType.exec,{labels[key]})
"""
    hooks+="""checkedMem527(function(a,v)
 if packet and pb(0)==3 and pw(8)==911 and phase986~='' and phase986~='upload165_entry' then
  local off=a-0x7f6500-word(0x1020)
  if off>=0 and off<1562 then mark986('read_'..phase986,off,v) end
 end
end,emu.callbackType.read,0x7f0000,0x7fffff)
"""
    lua=once(lua,"checkedMem527(function()rpc()end",hooks+"checkedMem527(function()rpc()end")
    lua=once(lua,"if a==0x6000 then rpc();if not firstPoll","""if a==0x6000 then rpc()
  if not packet and sent==retired and word(0x1226)==911 and empty986~=index then
   empty986=index;mark986('empty')
  end
  if not firstPoll""")
    return once(lua,"lastStatus=ack[1];sample516","""if pw(8)==911 and pb(0)==2 and pb(1)==5 and ack[1]==0 then
   local dst=0x10000+word(0x1020)+0x6500+pw(10)
   assert(word(0x1034)~=word(0x1032))
   for i=0,pw(12)-1 do assert(rd(dst+i)==pb(16+i),'literal WRAM mismatch') end
   mark986('literal',pw(10),pw(12))
  end
  lastStatus=ack[1];sample516""")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("tag",choices=("978returned","986high","986split","986fifo"))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("--damage",choices=("scroll","table"))
    p.add_argument("--palette",action="store_true")
    a=p.parse_args()
    d=directory(a.temp,a.phase,a.tag,"cold")
    assert sha(d/"client.sfc")==sha(PACKED/"sink165.sfc")
    cmds,_=packet_path(d,911)
    def instrument(lua):
        lua=observer(lua)
        if a.palette:
            lua=once(lua,"local function sample516(event,value)","""local expectedPal986=file('colors636-911.bin')
local function pal986(event)
 local back,live=0,0
 for i=0,511 do
  local v=expectedPal986:byte(i+1)
  if rd(0x16000+i)~=v then back=back+1 end
  if emu.read(i,emu.memType.snesCgRam)~=(v&(i%2==1 and 127 or 255)) then live=live+1 end
 end
 mark986(event,back,live)
end
local function sample516(event,value)""")
            lua=once(lua,"packet=requests[index];sample516","""packet=requests[index]
 if pw(8)==911 and pb(1)==3 and pw(10)==0 then
  assert(word(0x1034)==0 and word(0x1020)==0);pal986('before_palette')
 end
 sample516""")
            lua=once(lua,"lastStatus=ack[1];sample516","""if pb(0)==3 and ack[1]==1 and (pw(8)==909 or pw(8)==910) then
   pal986('ack'..pw(8))
  elseif pb(0)==1 and pw(8)==911 and ack[1]==0 then pal986('begin911') end
  lastStatus=ack[1];sample516""")
        if a.damage:
            off=0 if a.damage=="scroll" else 1121+192+162
            lua=once(lua,"phase986='seal';mark986(phase986)",f"""phase986='seal';mark986(phase986)
   local dst=0x10000+word(0x1020)+0x6500+{off}
   local prev=rd(dst);assert(prev~=0)
   emu.write(dst,0,emu.memType.snesWorkRam);mark986('damaged',{off},prev)""")
        return lua
    suffix=("-"+a.damage if a.damage else "")+("-palette" if a.palette else "")
    replay(a.temp,d,a.temp/f"nes-tail986-trace-{a.tag}-p{a.phase}{suffix}","control",cmds,911,
           "wram986" if a.damage else None,observe=instrument)
