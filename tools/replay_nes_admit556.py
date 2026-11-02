# SPDX-License-Identifier: MIT
"""Record instruction boundaries on the 192-byte map while replaying the independent consumer."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import replay_nes_frontier536 as frontier
import replay_nes_map527 as replay
from nes_raw506 import once
from replay_nes_grant555 import log_dma
from replay_nes_receipt548 import observe


def admission(script, labels):
    hooks = ["""local admission556=assert(io.open(ROOT..'/admission556.csv','w'))
admission556:write('index,event,clock,line\\n')
local function stamp556(event)
 if packet and pb(0)==2 and pb(1)==2 and pw(8)==954 and pw(10)==2432 then
  local st=emu.getState()
  admission556:write(string.format('%d,%s,%d,%d\\n',index,event,st.masterClock,st['ppu.scanline']))
  admission556:flush()
 end
end"""]
    for name in ('header','data','mark212','bits212','append212','literal1814','accepted','reply'):
        hooks.append(f"emu.addMemoryCallback(function()stamp556('{name}')end,emu.callbackType.exec,{labels[name]})")
    hooks.append("emu.addMemoryCallback(function()stamp556('DMA_start')end,emu.callbackType.write,0x420b)")
    hooks.append("""local expected556=nil
local summary556=assert(io.open(ROOT..'/bitmaps556.csv','w'))
summary556:write('bank,section,units\\n')
emu.addMemoryCallback(verify526(function()
 local section=emu.getState()['cpu.x']//2
 if section>2 then return end
 assert(not expected556)
 local unit=({16,32,64})[section+1]
 local first=({0,1024,1152})[section+1]+word(0x120a)//unit
 local count=word(0x120c)//unit
 local bank=word(0x1034)
 assert(count>0 and (bank==0 or bank==1))
 local bytes={}
 for i=0,151 do bytes[0x1280+i]=rd(0x1280+i) end
 for i=0,303 do bytes[0x1320+i]=rd(0x1320+i) end
 for bit=first,first+count-1 do
  local d=0x1280+bit//8;local v=0x1320+152*bank+bit//8
  local mask=1<<(bit%8)
  assert((bytes[d]&mask)==0);bytes[d]=bytes[d]|mask;bytes[v]=bytes[v]|mask
 end
 expected556=bytes
 summary556:write(string.format('%d,%d,%d\\n',bank,section,count))
end),emu.callbackType.exec,@MARK@)
emu.addMemoryCallback(verify526(function()
 if not expected556 then return end
 for at,v in pairs(expected556) do assert(rd(at)==v,'admission bitmap at '..at)end
 expected556=nil;summary556:flush()
end),emu.callbackType.exec,@APPEND@)""".replace('@MARK@',str(labels['mark212'])).replace('@APPEND@',str(labels['append212'])))
    return once(log_dma(script),'local function loaded()', '\n'.join(hooks)+'\nlocal function loaded()')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for k in ('client','trace','mesen','out'):
        p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args()
    a.frames=53
    labels=json.loads((a.client/'labels.json').read_text())
    limit=json.loads((a.client/'build.json').read_text())['map_chunk_B']
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit=str(limit))), patch.object(replay,'observer',observe):
        replay.run(a,edit_script=lambda s:admission(s,labels))
