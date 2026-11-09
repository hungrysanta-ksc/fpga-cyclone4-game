"""Same B instructions/timing through918; add values to the existing beam assertion."""
import runpy,subprocess
from pathlib import Path
from unittest.mock import patch
import test_nes_tile532 as tile
from nes_raw506 import once

if __name__=='__main__':
 schedule=tile.run_schedule;launch=subprocess.Popen
 def short(a,instrument,link_type,frames):return schedule(a,instrument,link_type,14)
 def popen(args,*pargs,**kwargs):
  if '--testRunner' in args:
   f=Path(args[args.index('--testRunner')+1]);s=f.read_text(encoding='utf8')
   if f.name=='capture.lua':
    s=once(s,'assert(beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount)',
     "assert(beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount,string.format('BEAM713 g=%d saved=%d/%d/%d current=%d/%d/%d elapsed=%d bytes=%d length=%d',word(0x1226),beam685.line,beam685.h,beam685.frame,st['ppu.scanline'],st['memoryManager.hClock'],st.frameCount,st.masterClock-beam685.clock,n,length))")
    f.write_text(s,encoding='utf8',newline='\n')
  return launch(args,*pargs,**kwargs)
 with patch.object(tile,'run_schedule',short),patch.object(subprocess,'Popen',popen):
  runpy.run_module('test_nes_rows713',run_name='__main__')
