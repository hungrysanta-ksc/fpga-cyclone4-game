# SPDX-License-Identifier: MIT
"""Record the original 753 PPU-port byte writes without changing its CPU schedule."""
import argparse
from pathlib import Path
from unittest.mock import patch
import replay_nes_map527 as replay
from nes_raw506 import once
from trace_nes_owner739 import observe


def run(a):
    a.frames=53
    def edit(s):
        s=once(s,'local function write(a,v)',"""local wire762=assert(io.open(ROOT..'/wire762.csv','w'))
wire762:write('event,g,clock,source,port,byte\\n')
local cursor762=0
local function write(a,v)
 if pending526 and pending526.n==1536 and (a==0x2118 or a==0x2119) then
  local src=regs[0x4302]+256*regs[0x4303]+cursor762
  wire762:write(string.format('write,%d,%d,%d,%d,%d\\n',pending526.g,emu.getState().masterClock,src,a,v))
  cursor762=(cursor762+1)%1536
  if cursor762==0 then wire762:flush() end
 end""")
        return s
    with patch.object(replay,'observe',observe):replay.run(a,edit_script=edit)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
