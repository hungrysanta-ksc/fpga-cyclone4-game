# SPDX-License-Identifier: MIT
"""Observe MDMAEN and its beam position on the unmodified cartridge ROM."""
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once


def instrument(script):
    tap = """local dma748=assert(io.open(ROOT..'/dma748.csv','w'))
dma748:write('g,clock,line,h,source,bytes\\n')
checkedMem527(function(_,enable)
 if enable~=1 then return end
 local g=word(0x1226)
 if g~=952 and g~=957 then return end
 local st=emu.getState()
 dma748:write(string.format('%d,%d,%d,%d,%d,%d\\n',g,st.masterClock,st['ppu.scanline'],
  st['memoryManager.hClock'],regs[0x4302]+256*regs[0x4303],regs[0x4305]+256*regs[0x4306]))
 dma748:flush()
end,emu.callbackType.write,0x420b)
"""
    return once(script, 'local function loaded()', tap + 'local function loaded()')


if __name__ == '__main__':
    popen = subprocess.Popen.__init__

    def launch(proc, args, *pos, **kw):
        if isinstance(args, (list, tuple)) and '--testRunner' in args:
            path = Path(args[args.index('--testRunner')+1])
            if path.name == 'capture.lua':
                path.write_text(instrument(path.read_text(encoding='utf8')), encoding='utf8', newline='\n')
        popen(proc, args, *pos, **kw)

    with patch.object(subprocess.Popen, '__init__', launch):
        runpy.run_module('test_nes_observer717', run_name='__main__')
