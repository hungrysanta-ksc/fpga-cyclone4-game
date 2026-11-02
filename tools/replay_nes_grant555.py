# SPDX-License-Identifier: MIT
"""Check every early byte and record the actual DMA register writes at generation 954."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import replay_nes_frontier536
import replay_nes_map527 as replay
from nes_raw506 import once
from replay_nes_receipt548 import observe


def log_dma(script):
    script = once(script, 'local function file(name)', """local dma555=assert(io.open(ROOT..'/dma555.csv','w'))
dma555:write('index,owned,clock,line,frame,port,src,dst,n\\n')
local function file(name)""")
    marker = 'sample516("ppu_dma",dmaLength)'
    return once(script, marker, marker + """
   if word(0x1226)==954 then
    local st=emu.getState()
    local function reg16(a)return (regs[a] or 0)+256*(regs[a+1] or 0)end
    dma555:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',index,packet and pb(0) or -1,
     st.masterClock,st['ppu.scanline'],st.frameCount,regs[0x4301],reg16(0x4302),reg16(0x2116)*2,dmaLength))
    dma555:flush()
   end
""")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('trace', 'client', 'mesen', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args()
    args.frames = 53
    limit = json.loads((args.client / 'build.json').read_text())['map_chunk_B']
    instrument = partial(replay_nes_frontier536.tile_observer, map_limit=str(limit))
    with patch.object(replay_nes_frontier536, 'tile_observer', instrument), patch.object(replay, 'observer', observe):
        replay.run(args, edit_script=log_dma)
