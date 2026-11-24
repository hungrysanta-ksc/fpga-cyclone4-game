"""Observe ownership and contiguous raw data at actual 65816 instruction boundaries."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw991 import PACKED
from nes_raw506 import once


def observe(script):
    labels=read(PACKED/"labels.json")
    capture="""local f991=assert(io.open(ROOT..'/ownership.csv','w'))
f991:write('event,clock,frame,line,h,active,target,cursor\\n')
local function rawMark991(event)
 local st=emu.getState()
 f991:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d\\n',event,st.masterClock,st.frameCount,st['ppu.scanline'],st['memoryManager.hClock'],word(0x1032),word(0x1034),word(0x108a)))
 f991:flush()
end
local function isRaw991()
 return packet and pw(8)==911 and pb(0)==2 and pb(1)==5 and pw(10)==1121 and pw(12)==201
end
"""
    for label in ("base_ready","accepted"):
        code= "if packet and pw(8)==911 then rawMark991('assign_base') end" if label=="base_ready" else """
 if packet and pw(8)==911 and pb(0)==1 then rawMark991('begin_valid')
 elseif packet and pw(8)==911 and pb(0)==7 then rawMark991('tile_valid')
 elseif isRaw991() then
  assert(word(0x108a)==1322 and word(0x1032)==1 and word(0x1034)==0)
  for j=0,191 do assert(rd(0x10000+0x6961+j)==pb(16+j)) end
  rawMark991('raw201_valid')
 end"""
        capture+=f"checkedMem527(function(){code} end,emu.callbackType.exec,{labels[label]})\n"
    capture+="""checkedMem527(function(a)
 if isRaw991() and a==0x7f6a20 then rawMark991('raw192_last_write') end
end,emu.callbackType.write,0x7f6a20)
checkedMem527(function(a,v)
 if packet and pw(8)==910 and v==15 then rawMark991('public910') end
end,emu.callbackType.write,0x2100)
"""
    return once(script,"checkedMem527(function()rpc()end",capture+"checkedMem527(function()rpc()end")


def trace(temp,phase,mode):
    folder=directory(temp,phase,"978returned" if mode=="ref" else "991"+mode,"cold")
    cmds,_=packet_path(folder,911)
    return replay(temp,folder,temp/f"nes-raw991-ownership-{mode}-p{phase}","control",cmds,911,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("ref","drain"))
    a=p.parse_args();trace(a.temp,a.phase,a.mode)
