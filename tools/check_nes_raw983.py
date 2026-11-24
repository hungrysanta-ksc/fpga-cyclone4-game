"""Locate real empty queue polls after the first literal of the compact raw row."""
import argparse
from pathlib import Path

from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once


def observe(lua):
    lua=once(lua,"local function sample516(event,value)", """local raw983=false
local log983=assert(io.open(ROOT..'/raw983.csv','w'))
log983:write('event,clock,frame,line,h,index,sent,retired,target,visible\\n')
local function record983(kind)
 local s=emu.getState()
 log983:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',kind,s.masterClock,s.frameCount,
  s['ppu.scanline'],s['memoryManager.hClock'],index,sent,retired,word(0x1034),word(0x1032)))
 log983:flush()
end
local function sample516(event,value)""")
    lua=once(lua,"lastStatus=ack[1];sample516", """if pw(8)==911 and pb(0)==2 and pb(1)==5 and (pw(10)==1121 or pw(10)==1322) then
   assert(ack[1]==0 and word(0x1034)~=word(0x1032),'candidate ownership')
   for i=0,pw(12)-1 do
    assert(rd(0x10000+word(0x1020)+0x6500+pw(10)+i)==pb(16+i),'restored section-5 byte')
   end
   raw983=true;record983(pw(10)==1121 and 'first' or 'last')
  end
  if pw(8)==911 and pb(0)==3 then raw983=false end
  lastStatus=ack[1];sample516""")
    return once(lua,"if a==0x6000 then rpc();if not firstPoll", """if a==0x6000 then rpc()
  if raw983 and not packet and sent==retired then record983('empty') end
  if not firstPoll""")


def run(temp,phase,tag,fault=None):
    d=directory(temp,phase,tag,"cold")
    c,_=packet_path(d,911)
    name=f"nes-983observer-{tag}-p{phase}"
    replay(temp,d,temp/(name+"-"+fault if fault else name),"control",c,911,fault,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int)
    p.add_argument("tag")
    p.add_argument("--fault",choices=("stop_decode","bad_seal"))
    a=p.parse_args()
    run(a.temp,a.phase,a.tag,a.fault)
