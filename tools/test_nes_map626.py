# SPDX-License-Identifier: MIT
"""Bind the independent idle-map observer to the selected descriptor's suffix."""
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once


def suffix_observer(script):
    anchor='  if word(0x4000+tail)==src then i=tail end'
    if anchor not in script or 'math.min(1152,word(0x4004+i))' not in script:
        return script
    return once(script,anchor+'''
  assert(word(0x4000+i)==src and word(0x4002+i)==dst and n==math.min(1152,word(0x4004+i)))''','''  local function matches(index)
   local size=word(0x4004+index)
   local delta=size-n
   return n==math.min(1152,size) and word(0x4000+index)+delta==src and word(0x4002+index)+delta==dst
  end
  assert(matches(i) or matches(tail),'selected map suffix')''')


def run(module):
    write=Path.write_text
    def observe(path, text, *args, **kwargs):
        if path.name=='capture.lua':
            if '--whole' in flags and 'n<=1152 and off%64' in text:
                text=once(text,'n<=1152 and off%64','(n<=1152 or (n==1344 and sample626 and sample626<=247)) and off%64')
                text=once(text,'local pending526=nil',"""local pending526=nil
local sample626
emu.addMemoryCallback(function()sample626=emu.getState()['ppu.scanline']end,emu.callbackType.read,0x2137)""")
                text=once(text,'n==math.min(1152,word(0x4004+i))','(n==math.min(1152,word(0x4004+i)) or (n==1344 and word(0x4004+i)==n))')
            elif '--whole' not in flags:
                text=suffix_observer(text)
        return write(path,text,*args,**kwargs)
    flags=set(sys.argv[1:])
    if '--whole' in flags:
        sys.argv.remove('--whole')
    with patch.object(Path,'write_text',observe):
        runpy.run_module(module,run_name='__main__')


if __name__=='__main__':
    run('test_nes_board611')
