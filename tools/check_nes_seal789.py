# SPDX-License-Identifier: MIT
"""Replay immutable arrivals and interrupt each real 64-byte row of the 931 receipt."""
import argparse
import csv
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as player
from nes_raw506 import once, sha
from trace_nes_owner739 import observe


def run(a):
    labels = json.loads((a.client / "labels.json").read_bytes())
    a.frames = 66 if a.row is None else 27
    def edit(script):
        hook = """local armed789=false
local log789=assert(io.open(ROOT..'/rows789.csv','w'))
log789:write('g,row,mask,clock,line\\n')
local function row789(i)
 if packet and pb(0)==3 and pw(8)==931 then
  local st=emu.getState()
  log789:write(string.format('%d,%d,%d,%d,%d\\n',pw(8),i,word(0x78),st.masterClock,st['ppu.scanline']))
  log789:flush()
  if word(0x78)==29 and i==STOPROW then armed789=true end
 end
end
""".replace("STOPROW", str(a.row if a.row is not None else -1))
        for i in range(3):
            hook += f"checkedMem527(function()row789({i})end,emu.callbackType.exec,{labels[f'row624_{i}']})\n"
        script = once(script, "local function loaded()", hook+"local function loaded()")
        if a.row is not None:
            script = once(script, "local FAULT=905", "local FAULT=931")
            script = once(script, "  assert(captured==commits)", "  assert(armed789 and word(0x1248)==26 and word(0x124a)==0)\n  assert(captured==commits)")
            script = once(script, "local MODE='normal'", "local MODE='stop789'")
            script = once(script, " if a==0x6001 then"," if a==0x6001 then\n  if armed789 then return 128 end")
        return script

    with patch.object(player, "observe", observe):
        try:
            player.run(a, edit_script=edit, compare_trace=lambda *_: {}, source_client=a.source_client)
        except AssertionError:
            if a.row is None:raise
            actual=json.loads((a.out/"result.json").read_bytes())
            assert actual["passed"] and actual["commits"]==26 and actual["last_status"]==0xe4
            assert sha(a.out/"retained.rgb")==sha(a.trace/"frame-930.rgb")
        else:
            assert a.row is None
    with (a.out/"rows789.csv").open() as f:
        rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    assert [r["row"] for r in rows]==([0] if a.row==0 else [0,2]) and all(r["mask"]==29 for r in rows)
    if a.row is not None:
        with (a.out/"window.csv").open() as f:
            after=[r for r in csv.DictReader(f) if int(r["clock"])>=rows[-1]["clock"] and r['g']=='931']
        assert not any(r["event"] in ("ppu_dma","reveal") for r in after)
        assert [int(r["value"]) for r in after if r["event"]=="ack" and r["op"]=="3"]==[0xe4]
    (a.out/"proof789.json").write_text(json.dumps(dict(client=sha(a.client/"sink165.sfc"),
        rows=rows, frames=a.frames if a.row is None else 26, STOP_row=a.row,
        retained=sha(a.out/"retained.rgb") if a.row is not None else None),indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("trace","client","source_client","mesen","out"):p.add_argument(k,type=Path)
    p.add_argument("--row",type=int,choices=(0,2))
    run(p.parse_args())
