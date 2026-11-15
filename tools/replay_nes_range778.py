# SPDX-License-Identifier: MIT
"""Replay two ordered map heads at an optimistic wire floor on the exact 65816."""
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from analyze_nes_output768 import csv_groups, one, read
from trace_nes_owner739 import observe


def run(args):
    args.frames = 66
    events = read(args.trace / "events.json")
    wire = [e for e in events if e.get("generation") == 969 and e.get("opcode") == "0xe1"]
    moved = []
    release = {}
    if args.after_rows:
        assert args.pair
        planner = one([e for e in events if e.get("generation")==969], "planner_enter")["clock"]
        for off in (1024, 1216):
            stores = [e["clock"] for e in events if e.get("generation")==969 and
                      e["event"]=="map_store757" and off<=e["offset"]<off+192]
            assert stores and min(stores)>planner
            release[off] = max(stores)

    def edit(script):
        for source in args.trace.glob("colors636-*.bin"):
            (args.out / source.name).write_bytes(source.read_bytes())
        path = args.out / "arrivals.tsv"
        rows = [s.split("\t") for s in path.read_text().splitlines()]
        indexes = [i for i, (_, h, _) in enumerate(rows[:-1])
                   if int.from_bytes(bytes.fromhex(h)[8:10], "little") == 969]
        clock = 0
        for i, tx in zip(indexes, wire, strict=True):
            head = bytes.fromhex(rows[i][1])
            off = int.from_bytes(head[10:12], "little")
            end = int(rows[i][0])
            assert abs(end - tx["clock"]) <= 1
            if head[1] == 2 and (off == 1216 or (args.pair and off == 1024)):
                # Zero ARM preparation, zero gaps and credit latency. Keep FIFO order and
                # the measured duration of the complete 211-byte E1 on the shared wire.
                assert tx["bytes"] == 211
                end = round(max(clock, release.get(off, 0)) + tx["clock"] - tx["start"])
                assert end < tx["clock"]
                rows[i][0] = str(end)
                moved.append((off, end))
            clock = end
        assert [o for o, _ in moved] == ([1024, 1216] if args.pair else [1216])
        path.write_text("".join("\t".join(r) + "\n" for r in rows), newline="\n")
        return script

    def compare(old, new):
        assert [r for r in old if int(r["g"]) < 969] == [r for r in new if int(r["g"]) < 969]
        groups = csv_groups(args.out / "window.csv")
        def seal(g, event):
            return one([e for e in groups[g] if e["op"] == 3], event)
        first = seal(968, "reveal")["frame"] + 1
        q = groups[969]
        idle = [e for e in q if e["event"] == "idle524"]
        dmas = [e for e in q if e["event"] == "ppu_dma" and e["clock"] < seal(969, "load")["clock"]]
        transfers = []
        for select, dma in zip(idle, dmas, strict=True):
            assert 0 < dma["clock"] - select["clock"] < 1000
            transfers.append(dict(frame=dma["frame"] - first + 1, line=dma["line"],
                                  selector=select["value"], bytes=dma["value"]))
        return dict(arrivals=moved, transfers=transfers, interval969=seal(969, "reveal")["frame"]-first+1,
                    seal969=seal(969, "load")["clock"], ack969=seal(969, "ack")["clock"],
                    ack970=seal(970, "ack")["clock"])

    with patch.object(replay, "observe", observe):
        replay.run(args, edit_script=edit, compare_trace=compare)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("trace", "out", "mesen", "client"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--pair", action="store_true")
    parser.add_argument("--after-rows", action="store_true")
    run(parser.parse_args())
