# SPDX-License-Identifier: MIT
"""Record SEAL DMA addresses and the final beam latch without changing the common schedule."""
import argparse
from pathlib import Path

import test_nes_raw506_joint as joint
import replay_nes_map527 as replay
from nes_raw506 import once
from test_nes_map526_schedule import observer
from trace_nes_map527 import CheckedLink, MapRuntime, observed, run_schedule


def seal_trace(s):
    s=once(s,'local function loaded()',r"""local dma528=assert(io.open(ROOT..'/seal528.csv','w'))
dma528:write('g,event,clock,line,h,bank,port,src,dst,bytes\n')
local function log528(event,n)
 if not packet or pb(0)~=3 or (pw(8)~=952 and pw(8)~=954) then return end
 local st=emu.getState()
 local h=st['memoryManager.hClock'] or st['ppu.hClock'] or -1
 if h<0 then for k,v in pairs(st) do if k:lower():match('%.hclock$') then h=v;break end end end
 dma528:write(string.format('%d,%s,%d,%d,%d,%d,%d,%d,%d,%d\n',pw(8),event,st.masterClock,st['ppu.scanline'],h,word(0x1034),
 regs[0x4301] or 0,(regs[0x4302] or 0)+256*(regs[0x4303] or 0),2*((regs[0x2116] or 0)+256*(regs[0x2117] or 0)),n))
 dma528:flush()
end
emu.addMemoryCallback(function()log528('latch',0)end,emu.callbackType.read,0x2137)
local function loaded()""")
    return once(s,'sample516("ppu_dma",dmaLength)','sample516("ppu_dma",dmaLength);log528("dma",dmaLength)')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture','trace'):
        p.add_argument('--'+n,type=Path,required=n in ('out','client','mesen'))
    p.add_argument('--start-clock',type=int)
    p.add_argument('--map526',action='store_true',default=True)
    a=p.parse_args()
    if a.trace:
        a.frames=53
        replay.observer=lambda s,labels:seal_trace(observer(s,labels))
        replay.run(a)
    else:
        joint.Runtime=MapRuntime
        run_schedule(a,lambda s,a:seal_trace(observed(s,a)),CheckedLink,frames=53)
