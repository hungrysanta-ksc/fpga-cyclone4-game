# SPDX-License-Identifier: MIT
"""Replay unchanged CPU bytes and trace actual map/queue arbitration at 951 and 957."""
import argparse
from pathlib import Path
import replay_nes_map527 as replay
from replay_nes_frontier536 import instrument
from nes_raw506 import once

def decode(s,labels):
    hooks=["local decode544=assert(io.open(ROOT..'/decode544.csv','w'));decode544:write('g,index,op,section,event,clock,line\\n')",
           """local seen544={}
local function decodeMark544(name)
 local g=word(0x1226);if g~=951 and g~=957 then return end
 local key=tostring(index)..':'..name;if seen544[key]then return end;seen544[key]=true
 local st=emu.getState()
 decode544:write(string.format('%d,%d,%d,%d,%s,%d,%d\\n',g,index,word(0x1200)&255,word(0x1201)&255,name,st.masterClock,st['ppu.scanline']));decode544:flush()
end"""]
    for label in ('header','packed_header181','data','data_size_ok','mark212','literal1814','repeat1814','zero_chunk516','accepted','reply'):
        hooks.append(f"emu.addMemoryCallback(function()decodeMark544('{label}')end,emu.callbackType.exec,{labels[label]})")
    return once(s,'local function loaded()','\n'.join(hooks)+'\nlocal function loaded()')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--decode',action='store_true')
    a=p.parse_args();a.frames=53
    def observer(s,l):
        s=once(instrument(s,l),'g~=910 and g~=951','g~=951 and g~=957')
        return decode(s,l) if a.decode else s
    replay.observer=observer
    replay.run(a)
