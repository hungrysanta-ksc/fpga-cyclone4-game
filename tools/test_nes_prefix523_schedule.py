# SPDX-License-Identifier: MIT
"""Close the loop with the MMC520 MCU and observe real prefix writes and ACKs."""
import argparse
import json
from pathlib import Path
from trace_nes_obj518 import ObjLink
from test_nes_trim514_schedule import run_schedule
from test_nes_window516 import instrument
from nes_raw506 import once


def observe(s,a):
    s=instrument(s,a)
    labels=json.loads((a.client/'labels.json').read_text())
    marker='local function loaded()'
    s=once(s,marker,f"""local prefixFrame523=nil
emu.addMemoryCallback(function()
 local i=word(0x1252);local bank=word(0x1034)
 assert(packet and pb(0)~=3 and bank~=word(0x1032) and i+8<word(0x1250),'prefix owner')
 local dst=word(0x4002+i);local n=word(0x4004+i)
 local bg=bank==0 and 0 or 0xc000;local obj=bank==0 and 0x4000 or 0x8000;local map=bank==0 and 0x6000 or 0xa000
 assert(n>0 and n<=2048 and ((dst>=bg and dst+n<=bg+16384) or (dst>=obj and dst+n<=obj+4096) or (dst>=map and dst+n<=map+4096)),'prefix destination')
 prefixFrame523=emu.getState().frameCount
 sample516('prefix523',i)
end,emu.callbackType.exec,{labels['issue523']})
"""+marker)
    s=once(s,'if dmaRemaining==1 then sample516("ppu_last") end',"""if dmaRemaining==1 then
    if prefixFrame523 then assert(emu.getState().frameCount==prefixFrame523,'prefix crossed VBlank');prefixFrame523=nil end
    sample516("ppu_last")
   end""")
    return s


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("arm","data","fixture","plans","client","mesen","out","calendar","driver503","capture"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--start-clock",type=int,default=3000000)
    run_schedule(p.parse_args(),observe,ObjLink,frames=53)
