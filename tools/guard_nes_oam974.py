"""Exercise arbitrary four-byte patterns, partial blocks and sticky STOP on the linked client."""
import argparse
from pathlib import Path
from unittest.mock import patch

from nes_oam974 import INLINE, WIDE, directory, packet_path, read, replay
from nes_raw506 import once


def run(temp,length,wide=False):
    folder=directory(temp,1,"974wide" if wide else "974inline","cold")
    out=temp/f"nes-oam974-{'wide-' if wide else ''}guard-{length}"
    labels=read((WIDE if wide else INLINE)/"labels.json")
    entry=labels["oam_prefix974" if wide else "oam_loop974"]
    packets,_=packet_path(folder,911)
    pattern=bytes.fromhex("29cc1693")
    which,= [i for i,p in enumerate(packets) if p[:2]==(911,8)]
    g,op,arrival,wire,bulk,source,duration=packets[which]
    data=bytearray.fromhex(wire)
    assert data[10:16]==bytes.fromhex("b00004005001")
    data[14:16]=length.to_bytes(2,"little")
    data[16:]=pattern
    packets[which]=(g,op,arrival,data.hex(),bulk,source,duration)
    prefix="""local entered974=false
local verified974=false
local before974,after974
local function target974()return packet and pw(8)==911 and pb(0)==8 end
local function proof974(name)
 local f=assert(io.open(ROOT..'/proof974.txt','a'));f:write(name,'\\n');f:close()
end
"""
    if length<=336 and length%4==0:
        prefix+=f"""
checkedMem527(function()
 if target974() then
  local a=0x10000+word(0x7a)
  before974=rd(a-1);after974=rd(a+{length})
 end
end,emu.callbackType.exec,{labels['literal_length227']})
checkedMem527(function()if target974() then entered974=true end end,emu.callbackType.exec,{entry})
checkedMem527(function()
 if target974() and entered974 and not verified974 then
  local a=0x10000+word(0x7a);local values={{41,204,22,147}}
  assert(rd(a-1)==before974 and rd(a+{length})==after974,'adjacent byte')
  for i=0,{length-1} do assert(rd(a+i)==values[1+i%4],'pattern byte '..i) end
  verified974=true;proof974('exact bytes and neighbours before STOP')
 end
end,emu.callbackType.exec,{labels['service']})
"""
        fault="stop_decode"
    else:
        prefix+=f"""checkedMem527(function()if target974() then proof974('range rejected') end end,
emu.callbackType.exec,{labels['bad_packet']})
checkedMem527(function()assert(not target974(),'invalid range entered expansion')end,
emu.callbackType.exec,{entry})
"""
        fault="bad_seal"
    orig=Path.read_text
    def instrument(path,*args,**kwargs):
        s=orig(path,*args,**kwargs)
        if path==folder/"capture.lua":
            s=once(s,"local function step920(key)",prefix+"local function step920(key)")
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if target974() and entered974 then assert(verified974);return 128 end")
        return s
    with patch.object(Path,"read_text",instrument):
        result=replay(temp,folder,out,"control",packets,911,fault)
    assert (out/"proof974.txt").read_text().splitlines()==[
        "exact bytes and neighbours before STOP" if fault=="stop_decode" else "range rejected"]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("length",type=int,choices=(8,12,332,336,334,340))
    p.add_argument("--wide",action="store_true")
    a=p.parse_args()
    print(run(a.temp,a.length,a.wide))
