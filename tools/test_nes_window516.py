# SPDX-License-Identifier: MIT
"""Time section 5, independent SEAL checks, VRAM and the final PPU transaction on the common clock."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_trim514_schedule import run_schedule

def instrument(s,a):
    labels=json.loads((a.client/'labels.json').read_text())
    body=(a.client/'body.bin').read_bytes()
    s=once(s,'local function loaded()',"""local trace516=assert(io.open(ROOT..'/window.csv','w'))
trace516:write('g,index,op,section,event,clock,line,frame,value\\n')
local borrowedFrame=nil
local function sample516(event,value)
 if not packet then return end
 local st=emu.getState()
 if event=='borrow516' then borrowedFrame=st.frameCount end
 if event=='ack' and value==1 and borrowedFrame then
  assert(st.frameCount==borrowedFrame and st['ppu.scanline']>=225,'borrowed display crossed VBlank')
  borrowedFrame=nil
 end
 trace516:write(string.format('%d,%d,%d,%d,%s,%d,%d,%d,%d\\n',pw(8),index,pb(0),pb(1),event,st.masterClock,st['ppu.scanline'],st.frameCount,value or 0))
 if event=='ack' then trace516:flush() end
end
local function loaded()""")
    s=once(s,'packet=requests[index];reads=0;','packet=requests[index];sample516("load");reads=0;')
    s=once(s,'lastStatus=ack[1]','lastStatus=ack[1];sample516("ack",lastStatus)')
    s=once(s,'dmaRemaining=dmaLength','dmaRemaining=dmaLength;sample516("ppu_dma",dmaLength)')
    s=once(s,"if a==0x420b and v==1 and(regs[0x4301]", """if a==0x420b and v==1 and regs[0x4301]==0x80 and regs[0x4300]==8 then
   local n=(regs[0x4305] or 0)+256*(regs[0x4306] or 0)
   assert(pb(0)==5 and pb(1)==5 and pw(16)==0 and n>0 and n<=64 and regs[0x4304]==0x40 and regs[0x4302]==16 and regs[0x4303]==0,'fixed DMA owner')
   sample516('zero_dma',n)
  end
  if a==0x420b and v==1 and(regs[0x4301]""")
    s=once(s,'if a==0x2100 and v==15 then assert','if a==0x2100 and v==15 then sample516("reveal");assert')
    s=once(s,'if visible then\n   assert(dmaRemaining','if visible then\n   if dmaRemaining==1 then sample516("ppu_last") end\n   assert(dmaRemaining')
    hooks={name:labels[name] for name in ('seal','validate181','coverage212','upload165_entry','wait169','final212',
                                         'final_upload212_same_blank212','select169','hdma181')}
    for name in ('wait_final516','fresh516','borrow516','zero_chunk516'):
        if name in labels:hooks[name]=labels[name]
    jsr=bytes([0x20])+int(labels['wait169']&65535).to_bytes(2,'little')
    sites=[i for i in range(len(body)) if body.startswith(jsr,i)]
    for i in sites:hooks['wait_return_'+str(i)]=0x7e2000+i+3
    lines=[f"emu.addMemoryCallback(function()sample516('{name}')end,emu.callbackType.exec,{pc})" for name,pc in hooks.items()]
    return once(s,'local sequence=0;', '\n'.join(lines)+'\nlocal sequence=0;')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--start-clock',type=int,default=3000000)
    run_schedule(p.parse_args(),instrument)
