"""Bound the physical tile and post-tile intervals in MMC955/966's late demo."""
import argparse
import csv
import json
import struct
from collections import Counter
from pathlib import Path

from analyze_nes_game215 import crc8
from analyze_nes_obj967 import WORKLOAD_FIELDS, capture, matched_workloads
from analyze_nes_supply485_hardware import fields
from read_nes_frame900 import HEADER, PERIOD
from read_nes_supply905 import MS, ROW, decode


def classify(low, high):
    if low > PERIOD:
        return "long"
    if high < PERIOD:
        return "short"
    return "uncertain"


def profile(directory, edition):
    verified = capture(directory, edition)
    path = directory / f"nes-frame-mmc{edition}.bin"
    data = path.read_bytes()
    trace = decode(path, edition)
    if trace["mode"] not in (0, 2) or any(not 5500 <= r["tick"] < 6000 for r in trace["rows"]):
        raise ValueError("expected the late demo")
    result = []
    for idx, r in enumerate(trace["rows"]):
        if not r["chunks"]:
            raise ValueError("these pinned runs have a descriptor for every generation")
        tick, gen, bg, ia, ea, probe, obj, dirty, valid, bank, header, desc = ROW.unpack_from(
            data, HEADER.size + idx * ROW.size)
        origin, query, last = struct.unpack_from("<3H", header, 6)
        supply = (last - origin) & 1023
        after = (query - last) & 1023
        if (tick, gen) != (r["tick"], r["generation"]) or supply + after != ((query-origin) & 1023):
            raise ValueError("record identity or event order")
        # Independent clocks: FPGA edges have one coarse tick of difference
        # uncertainty. ARM stamps are truncated to units of 512 cycles.
        # now is sampled before the query and probe spans the complete query.
        arm_tick = MS / 64
        source_bounds = [max(0, supply-1)*MS, (supply+1)*MS]
        tail_bounds = [max(0, (after-1)*MS - (ea+probe+2)*arm_tick),
                       (after+1)*MS - ea*arm_tick]
        if tail_bounds[1] < tail_bounds[0] or ea > ia:
            raise ValueError("invalid post-tile bounds")
        item = {k: r[k] for k in ("generation", "tick", *WORKLOAD_FIELDS, "input_to_final_ACK_ms")}
        item.update(supply_ms=[round(v, 4) for v in source_bounds],
                    post_tile_ms=[round(v, 4) for v in tail_bounds],
                    supply=classify(*source_bounds), post_tile=classify(*tail_bounds))
        result.append(item)
    counts = Counter((r["supply"], r["post_tile"]) for r in result)
    early_long = [r["generation"] for r in result if r["post_tile"] == "long" and r["supply_ms"][1] < 2]
    budget = fields((directory / f"nes-budget-mmc{edition}.txt").read_text(encoding="utf-8-sig"))
    if (budget["tick_ms"] != "10" or budget["bin_basis"] != "FRAME_START_NOT_SCENE"
            or int(budget["b11"].split(",")[0],16) != len(result)):
        raise ValueError("frame-start budget does not match the trace")
    return dict(bin_sha256=verified["sha256"], displayed=trace["displayed55"],
                displayed_1_30_and_30_60=[int(n) for n in budget["display_1_30_60"].split(",")],
                summaries=len(result), dropped=trace["dropped"],
                classes={f"{s}/{p}": n for (s,p),n in sorted(counts.items())},
                post_long_supply_under_2ms=early_long, rows=result)


def compare(directory):
    runs = {e: profile(directory,e) for e in (955,966)}
    pairs = matched_workloads(runs[955]["rows"], runs[966]["rows"])
    comparisons = []
    for a,b in pairs:
        item = {"previous": a["generation"], "current": b["generation"],
                "ack_delta_ms": round(b["input_to_final_ACK_ms"] - a["input_to_final_ACK_ms"], 3)}
        for field in ("supply_ms","post_tile_ms"):
            lo, hi = a[field]
            new_lo, new_hi = b[field]
            item[field+"_delta"] = [round(new_lo-hi, 3),round(new_hi-lo, 3)]
        comparisons.append(item)
    both = [b["generation"] for a,b in pairs if a["post_tile"] == b["post_tile"] == "long"]
    quick = [b["generation"] for a,b in pairs if a["post_tile"] == b["post_tile"] == "long"
             and max(a["supply_ms"][1], b["supply_ms"][1]) < 2]
    return dict(period_ms=PERIOD,runs=runs,pairs=comparisons,both_long_after_tile=both,
                both_long_after_tile_with_supply_under_2ms=quick)


def replay_boundaries(temp, phase):
    """Contrast two meanings of a long post-tile interval using the saved 978 run."""
    folder = temp / f"nes-tile821-obj-jointmirror-p{phase}-978returned-cold-pair"
    with (folder / "window.csv").open(newline="") as f:
        window = list(csv.DictReader(f))
    with (folder / "producer.jsonl").open() as f:
        tiles = [json.loads(line) for line in f]
    events = json.loads((folder / "events.json").read_bytes())
    reference = Path(__file__).resolve().parents[1] / "analysis/capture978-results.json"
    pinned = json.loads(reference.read_bytes())["phases"][str(phase)]["978returned"]
    stages = {}
    for gen in range(906, 913):
        group = [r for r in window if r["g"] == str(gen) and r["op"] == "3"]
        points = {r["event"]: int(r["clock"]) for r in group}
        ack, = (r for r in group if r["event"] == "ack")
        seq = int(ack["index"])
        e9 = next(e for e in events if e.get("opcode") == "0xe9" and e["generation"] == gen)
        last = max(t["producer"] for t in tiles if t["generation"] == gen)
        replies = (e for e in events if e.get("opcode") == "0xe0" and e["generation"] == gen)
        for reply in replies:
            data = bytes.fromhex(reply["reply"])
            if len(data) != 20 or crc8(data[1:19]) != data[19]:
                raise ValueError("invalid E0")
            if (int.from_bytes(data[3:5],"big") == int.from_bytes(data[5:7],"big") == seq
                    and data[7:9] == bytes((1,3)) and int.from_bytes(data[15:17],"little") == gen):
                break
        else:
            raise ValueError("missing final E0")
        times = [e9["start"], last, points["load"], points["seal"], points["reveal"],
                 points["ack"], reply["clock"]]
        if times != sorted(times) or int(ack["frame"]) != pinned["displays"][gen-905]:
            raise ValueError("inconsistent 978 replay")
        if gen == 912 and points["ack"] != pinned["ACK912"]:
            raise ValueError("wrong replay baseline")
        stages[gen] = dict(zip(("E9_issue", "last_tile", "SEAL_header", "SEAL_entry",
                                "show", "final_ACK", "E0_reply"), times, strict=True))
        previous, = (r for r in window if r["g"] == str(gen-1) and r["event"] == "reveal")
        last_dma = max(int(r["clock"]) for r in window if r["g"] == str(gen) and r["event"] == "ppu_last")
        stages[gen].update(previous_show=int(previous["clock"]), last_dma=last_dma)
        if not stages[gen]["previous_show"] < last_dma <= points["reveal"]:
            raise ValueError("last PPU transfer outside the display interval")
        # Test the proposed five coarse observer timestamps against the original
        # reveal counter. Values in real BINs will also need same-generation flags.
        names = ("previous_show", "SEAL_header", "last_dma", "show", "final_ACK")
        quant = 21477272 * MS / 1000
        stamp = [int(stages[gen][name] / quant) for name in names]
        if max(stamp)-min(stamp) >= 1024:
            raise ValueError("ambiguous observer wrap")
        prev, seal, dma, show, ack_tick = (n & 1023 for n in stamp)
        spacing = ((show-prev) & 1023)*MS
        vb = pinned["displays"][gen-905] - pinned["displays"][gen-906]
        if round((spacing-MS)/PERIOD) != vb or round((spacing+MS)/PERIOD) != vb:
            raise ValueError("quantized display interval ambiguous")
        stages[gen]["coarse_example"] = dict(show_vblanks=vb, seal_to_show_ms=round(((show-seal)&1023)*MS,3),
                                              dma_end_to_show_ms=round(((show-dma)&1023)*MS,3),
                                              show_to_ACK_ms=round(((ack_tick-show)&1023)*MS,3))
    return stages


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("captures",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--replay-root", type=Path)
    args = p.parse_args()
    report = compare(args.captures)
    if args.replay_root:
        report["replay978_master_hz"] = 21477272
        report["replay978"] = {p: replay_boundaries(args.replay_root,p) for p in (1,2)}
    args.output.write_bytes((json.dumps(report, indent=2)+"\n").encode())
