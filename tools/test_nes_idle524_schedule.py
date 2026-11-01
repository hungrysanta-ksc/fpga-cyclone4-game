# SPDX-License-Identifier: MIT
"""Observe idle DMA on the same two ARM/65816 timelines used for MMC520 and 523."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_window516 import instrument
from test_nes_trim514_schedule import run_schedule
from trace_nes_obj518 import ObjLink


def observe(s,a):
    labels=json.loads((a.client/'labels.json').read_text())
    s=instrument(s,a)
    anchor=" if not packet then return end\n local st=emu.getState()"
    s=once(s,anchor,""" if not packet then
  if event~='idle524' and event~='ppu_dma' and event~='ppu_last' then return end
  local st=emu.getState()
  trace516:write(string.format('%d,%d,-1,-1,%s,%d,%d,%d,%d\\n',word(0x1226),index,event,st.masterClock,st['ppu.scanline'],st.frameCount,value or 0))
  return
 end
 local st=emu.getState()""")
    return once(s,'local function loaded()',f"""emu.addMemoryCallback(function()
 local i=word(0x1252);local bank=word(0x1034)
 assert(not packet and word(0x1228)==1 and bank~=word(0x1032) and i+8<word(0x1250),'idle owner')
 local dst=word(0x4002+i);local n=word(0x4004+i)
 local bg=bank==0 and 0 or 0xc000;local obj=bank==0 and 0x4000 or 0x8000;local map=bank==0 and 0x6000 or 0xa000
 assert(n>0 and n<=2048 and ((dst>=bg and dst+n<=bg+16384) or (dst>=obj and dst+n<=obj+4096) or (dst>=map and dst+n<=map+4096)),'idle destination')
 sample516('idle524',i)
end,emu.callbackType.exec,{labels['grant524']})
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("arm","data","fixture","plans","client","mesen","out","calendar","driver503","capture"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--start-clock",type=int,required=True)
    run_schedule(p.parse_args(),observe,ObjLink,frames=53)
