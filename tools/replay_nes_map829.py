"""Run the linked MMC826 consumer against a read-side expanding packet aperture."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch
from nes_raw506 import once
from prepare_nes_map828 import PROBES, OUT
from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main


def monitor(s, lut=None, seed=None):
    decl="""
local function hex829(b)return (b:gsub('.',function(c)return string.format('%02x',c:byte())end))end
local compressed829=false
local cursor829=16
local reads829=assert(io.open(ROOT..'/reads829.txt','w'))
"""
    if seed:
        decl+="""
local old=assert(io.open(SEED,'rb'));local buf=old:read('*a');old:close();assert(#buf==8192)
for bank=0,1 do for i=0,4095 do emu.write(0x15000+bank*32768+i,buf:byte(1+bank*4096+i),emu.memType.snesWorkRam) end end
""".replace("SEED",json.dumps(seed.as_posix()))
    if lut:
        decl+="""
local rom829={}
for line in io.lines(LUT) do
 local key,val=line:match('^(%x+) (%x+)$')
 rom829[key]=string.gsub(val,'%x%x',function(v)return string.char(tonumber(v,16)) end)
end
""".replace("LUT",json.dumps(lut.as_posix()))
    load="""
 packet=requests[index]
 compressed829=pb(0)==9 and pb(1)==2
 if compressed829 then
  local wire=packet;cursor829=16
  reads829:write('P ',hex829(wire),'\\n')
  VIEW
 end
 sample516("load")
"""
    view="""local n=pw(12);assert((n==18 or n==36 or n==54) and #wire==16+n)
  local body=''
  for i=17,#wire,18 do body=body..wire:sub(i,i+17)..string.rep(string.char(0),46) end
  packet=string.char(2)..wire:sub(2,12)..string.char(#body,0)..wire:sub(15,16)..body"""
    s=once(s,"local index,retired",decl+"\nlocal index,retired")
    s=once(s,' packet=requests[index];sample516("load")',load.replace("VIEW","packet=assert(rom829[hex829(wire):lower()])" if lut else view).rstrip())
    s=once(s,"return pb(a-0x400000)","""local off=a-0x400000;local val=pb(off)
 if compressed829 then
  reads829:write(string.format('R %02x %02x\\n',off,val))
  if off>=16 then assert(cursor829==off);cursor829=off+1 end
 end
 return val """)
    s=once(s,"  lastAck=string.char(table.unpack(ack));","""  if compressed829 then
   assert(cursor829==#packet and ack[2]==2 and ack[1]==0)
   reads829:write('A ',hex(string.char(table.unpack(ack))),'\\n');reads829:flush()
   ack[2]=9
  end
  lastAck=string.char(table.unpack(ack));""")
    return s


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("group",choices=("earlyB","change","demoB"));p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path);p.add_argument("budget",type=Path)
    p.add_argument("--lut",type=Path);p.add_argument("--seed",type=Path)
    p.add_argument("--split",action="store_true")
    p.add_argument("--policy",choices=("two","one"))
    p.add_argument("--tag-suffix",default="")
    a=p.parse_args()
    clips=PROBES/"nes-trial825/data" if a.group=="change" else PROBES/"nes-tile821"/("extra01" if a.group=="earlyB" else "demo-extra01")
    tag="829cold" if a.seed else "829rtl" if a.lut else "829ref2"
    if a.split: tag+="split"
    arm=PROBES/'nes-map829/link-split/src' if a.split else OUT/'link-right/src'
    if a.policy:
        tag+=a.policy
        arm=PROBES/'nes-map829'/('link-'+a.policy)/'src'
    tag+=a.tag_suffix
    lookup=a.temp/"nes-demo825-cache/hits.json" if a.group=="change" else MirrorLink.lookup_file
    with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]),patch.object(MirrorLink,"lookup_file",lookup):
        main(clips,a.group,"jointmirror",a.phase,a.temp,arm=arm,link_class=MirrorLink,
             adapt_template=lambda s: monitor(s,a.lut,a.seed))
