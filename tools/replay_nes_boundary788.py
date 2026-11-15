# SPDX-License-Identifier: MIT
"""Replay checked Q arrivals, measuring the real idle-DMA start and its return."""
import argparse
import csv
from unittest.mock import patch
from pathlib import Path

import replay_nes_map527 as player
from analyze_nes_output768 import read
from nes_raw506 import once
from trace_nes_owner739 import observe


def run(args):
    args.frames = 66
    labels = read(args.client / "labels.json")
    def edit(script):
        hook = """local grants788=assert(io.open(ROOT..'/grants788.csv','w'))
grants788:write('event,g,clock,frame,line,blank,bytes\\n')
local amount788=nil
local function grant788(event)
 local st=emu.getState()
 local n=emu.read(0x4305,emu.memType.cpu) + 256*emu.read(0x4306,emu.memType.cpu)
 if event=='start' then amount788=n end
 assert(amount788 and st['ppu.scanline']>=225 and st['ppu.scanline']<=261,'idle DMA escaped VBlank')
 grants788:write(string.format('%s,%d,%d,%d,%d,%d,%d\\n',event,word(0x1226),st.masterClock,st.frameCount,st['ppu.scanline'],1,amount788))
 grants788:flush()
 if event=='end' then amount788=nil end
end
"""
        for event, name in (("start", "dma_start680"), ("end", "dma_retired680")):
            hook += f"checkedMem527(function()grant788('{event}')end,emu.callbackType.exec,{labels[name]})\n"
        return once(script, "local function loaded()", hook + "local function loaded()")
    def compare(_, rows):
        grants = list(csv.DictReader((args.out / "grants788.csv").open()))
        starts, ends = grants[::2], grants[1::2]
        assert len(starts) == len(ends) > 0
        for start, end in zip(starts, ends):
            assert start['event'] == 'start' and end['event'] == 'end'
            assert start['frame'] == end['frame'] and start['g'] == end['g']
            assert int(start['clock']) < int(end['clock'])
        return dict(idle_DMA=len(starts), last_return_line=max(int(r["line"]) for r in ends))
    with patch.object(player, "observe", observe):
        player.run(args, edit_script=edit, compare_trace=compare, source_client=args.source_client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("trace", "client", "source_client", "mesen", "out"):
        parser.add_argument(key, type=Path)
    run(parser.parse_args())
