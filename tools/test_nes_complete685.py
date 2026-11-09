"""Actual684 ARM/685 CPU with independent deadline/range validation."""
from pathlib import Path
from unittest.mock import patch
import test_nes_progress680 as progress
from test_nes_raw506_joint import Runtime
from test_nes_receive682 import observe as receive
from test_nes_bg684 import observe
from nes_raw506 import once

def budget_lua685(s,a):
    s=once(s,'local pending526=nil', '''local pending526=nil
local beam685=nil
local log685=assert(io.open(ROOT..'/budget685.csv','w'))
log685:write('generation,clock,latch_clock,line,h,bytes,range\\n');log685:flush()
emu.addMemoryCallback(function()
 local st=emu.getState()
 beam685={clock=st.masterClock,line=st['ppu.scanline'],h=st['memoryManager.hClock'],frame=st.frameCount}
end,emu.callbackType.read,0x2137)''')
    s=once(s,'n<=1152 and off%64==0','n<=1536 and off%64==0')
    s=once(s,'assert(word(0x4000+i)==src and word(0x4002+i)==dst and n==math.min(1152,word(0x4004+i)))', '''local length=word(0x4004+i);local st=emu.getState()
  assert(beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount)
  assert(st.masterClock-beam685.clock<3*1364,'stale DMA beam')
  local allowed=(beam685.line<=248 and length<=1536) and length or math.min(length,1152)
  assert(word(0x4000+i)==src and word(0x4002+i)==dst and n==allowed)
  log685:write(string.format('%d,%d,%d,%d,%d,%d,%d\\n',word(0x1226),st.masterClock,beam685.clock,beam685.line,beam685.h,n,length));log685:flush()''')
    return s

if __name__=='__main__':
    # Retain the exact680 real-CPU event bridge and684 ARM observations. Only
    # its independent old fixed1152B oracle changes to a measured beam bound.
    source=Path(progress.__file__).read_text()
    source=once(source,'    return s\n\n\ndef checked_exchange():','    return budget_lua685(s,a)\n\n\ndef checked_exchange():')
    with patch.object(Runtime,'__init__',observe(receive(Runtime.__init__))):
        exec(compile(source,progress.__file__,'exec'),dict(__name__='__main__',__file__=progress.__file__,budget_lua685=budget_lua685))
