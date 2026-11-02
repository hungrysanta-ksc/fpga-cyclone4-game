# SPDX-License-Identifier: MIT
"""Replay the closed-loop arrivals and check every native block move before decode."""
import argparse
import json
from pathlib import Path

import replay_nes_map527 as replay
from replay_nes_front544 import decode
from replay_nes_frontier536 import instrument
from nes_raw506 import once


def observer(source, labels):
    source=decode(once(instrument(source,labels),'g~=910 and g~=951','g~=951 and g~=957'),labels)
    source=once(source,'local function loaded()',f"""local copying546=false
local count546=0
local headers546=assert(io.open(ROOT..'/headers546.csv','w'))
headers546:write('index,start,finish,reads\\n')
local edge546,before546,after546
emu.addMemoryCallback(function()
 assert(packet and not copying546)
 copying546=true;count546=0;edge546=emu.getState().masterClock
 before546=rd(0x11ff);after546=rd(0x1210)
end,emu.callbackType.exec,{labels['header']})
emu.addMemoryCallback(function()
 assert(copying546 and count546==16)
 local st=emu.getState()
 assert(st['cpu.x']==16 and st['cpu.y']==0x1210)
 for i=0,15 do assert(rd(0x1200+i)==pb(i),'header copy') end
 assert(rd(0x11ff)==before546 and rd(0x1210)==after546)
 headers546:write(string.format('%d,%d,%d,%d\\n',index,edge546,st.masterClock,count546))
 copying546=false
end,emu.callbackType.exec,{labels['header']+9})
local function loaded()""")
    return once(source,"assert(packet and a-0x400000<#packet,'unowned packet')",
                "if copying546 then assert(a==0x400000+count546);count546=count546+1 end;assert(packet and a-0x400000<#packet,'unowned packet')")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','mesen','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--frames',type=int,default=53)
    args=parser.parse_args()
    labels=json.loads((args.client/'labels.json').read_text())
    offset=labels['header']-0x7e2000
    assert (args.client/'body.bin').read_bytes()[offset:offset+9]==bytes.fromhex('a0 00 12 a9 0f 00 54 00 40')
    replay.observer=observer
    replay.run(args)
