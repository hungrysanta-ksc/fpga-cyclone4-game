# SPDX-License-Identifier: MIT
"""Isolate the line-252 decision on actual 65816 code with frame-952 arrivals held fixed."""
import argparse
from functools import partial
import json
from pathlib import Path
from unittest.mock import patch

import observe_nes_repeat545
from nes_raw506 import once
from replay_nes_quiet608 import focus, frontier, replay
from test_nes_quiet608 import observe as palette_observer


def run(a):
    old,new=[(client/'body.bin').read_bytes() for client in (a.client,a.later)]
    assert len(old)==len(new)
    pc,=[i for i in range(len(old)) if old[i]!=new[i]]
    assert old[pc-1:pc+1]==bytes((0xc9,252)) and new[pc]==253
    labels=json.loads((a.client/'labels.json').read_text())
    def instrument(s):
        return once(s,'local function loaded()',f"""local switched616=false
emu.addMemoryCallback(function()
 if not switched616 and word(0x1226)==952 then
  assert(emu.read({0x2000+pc},emu.memType.snesWorkRam)==252)
  emu.write({0x2000+pc},253,emu.memType.snesWorkRam)
  switched616=true
  local f=assert(io.open(ROOT..'/switch.txt','w'));f:write(emu.getState().masterClock);f:close()
 end
end,emu.callbackType.exec,{labels['prefix523']})
local function loaded()""")
    def check(before,after):
        def prefix(rows):
            return [r for r in rows if int(r['g'])<952]
        assert prefix(before)==prefix(after)
        def frame(rows):
            selected=[r for r in rows if int(r['g'])==952]
            dma=[(int(y['line']),int(x['value'])-65536,int(y['value'])) for x,y in zip(selected,selected[1:])
                 if x['event']=='idle524' and int(x['value'])>=65536 and y['event']=='ppu_dma']
            seal=[r for r in selected if r['op']=='3']
            def event(k):
                r,=[r for r in seal if r['event']==k]
                return int(r['clock'])
            return dict(early_map=dma,SEAL_load=event('load'),reveal=event('reveal'),ACK=event('ack'),
                        final_waits=sum(r['event']=='wait169' and int(r['clock'])>=event('final212') for r in seal))
        return dict(identical_prefix_events=len(prefix(before)),switch_clock=int((a.out/'switch.txt').read_text()),
                    before=frame(before),after=frame(after))
    a.frames=48
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')), \
         patch.object(replay,'observer',partial(focus,generation=952)), \
         patch.object(observe_nes_repeat545,'observe',palette_observer):
        replay.run(a,edit_script=instrument,compare_trace=check)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('client','later','trace','out','mesen'):
        parser.add_argument('--'+k,type=Path,required=True)
    run(parser.parse_args())
