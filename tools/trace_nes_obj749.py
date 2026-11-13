# SPDX-License-Identifier: MIT
"""Observe the 694 WRAM descriptor queue through the VBlank of the 957 long DMA."""
import argparse
from pathlib import Path
from unittest.mock import patch

from analyze_nes_owner739 import read
from nes_raw506 import once
import replay_nes_map527 as replay
import trace_nes_owner739 as owner


def run(args):
    labels = read(args.client/'labels.json')
    def observe_queue(script):
        code = """
local q749=assert(io.open(ROOT..'/queue749.csv','w'))
q749:write('path,clock,frame,line,h,head,tail,occupancy,descriptors\\n')
local f749=-1
local seen749={}
local function queue749(path)
 if word(0x1226)~=957 then return end
 local st=emu.getState()
 if path=='MDMAEN' and regs[0x4302]+256*regs[0x4303]==22528 and
     regs[0x4305]+256*regs[0x4306]==1536 then f749=st.frameCount end
 if st.frameCount~=f749 or st['ppu.scanline']<225 then return end
 local h,t=word(0x1252),word(0x1250)
 local key=path..'/'..st['ppu.scanline']..'/'..h..'/'..t..'/'..sent..'/'..retired
 if seen749[key] then return end
 seen749[key]=true
 local ds={}
 for i=h,t-1,8 do ds[#ds+1]=string.format('%04X:%d',word(0x4000+i),word(0x4004+i)) end
 q749:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d,%s\\n',path,st.masterClock,st.frameCount,
  st['ppu.scanline'],st['memoryManager.hClock'],h,t,sent-retired,table.concat(ds,' ')))
end
checkedMem527(function()queue749('MDMAEN')end,emu.callbackType.write,0x420b)
"""
        for name in ('prefix523','tail532','selected526','defer_beam','late_tile681','large_tile681','ready524','service'):
            code += f"checkedMem527(function()queue749('{name}')end,emu.callbackType.exec,{labels[name]})\n"
        return once(script,'local function loaded()',code+'local function loaded()')
    args.frames=53
    with patch.object(replay,'observe',owner.observe):
        replay.run(args,edit_script=observe_queue)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('client','trace','mesen','out'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
