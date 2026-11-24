"""Validate the 907 deadline bound and compare alternate 912 bank schedules."""
import argparse
import math
from pathlib import Path

from check_nes_output970 import counters
from check_nes_plan975 import directory, read, sha
from check_nes_blank959 import rows
from nes_blank959 import ORIGIN
from nes_hdma990 import PACKED
from replay_nes_ready999 import releases
from test_nes_banks557 import MASTER
import json


def seal_floor(folder):
    points = {v[0]: list(map(int, v[1:])) for v in
              (s.split() for s in (folder / "cost999.txt").read_text().splitlines())}
    body = (PACKED / "body.bin").read_bytes()
    widths = {}
    for width, codes in (
        (2, "29 49 64 65 69 80 85 89 90 a0 a2 a5 a9 b0 b7 c0 c2 c5 c9 d0 e0 e2 e9 f0"),
        (3, "19 20 4c 6d 8d 9c 9d ac ad ae bd cd dd"),
        (4, "af bf"),
    ):
        widths.update({int(code, 16): width for code in codes.split()})
    result = {}
    for name in ("validated", "upload"):
        hits = [tuple(map(int, s.split())) for s in
                (folder / f"{name}999-hits.txt").read_text().splitlines()]
        assert all(0 <= pc - ORIGIN < len(body) for pc, n in hits)
        instructions = sum(n for pc, n in hits)
        fetches = sum(n * widths.get(body[pc - ORIGIN], 1) for pc, n in hits)
        clock, cpu, count, signature = points[name]
        assert instructions == count
        cycles = cpu - points["begin"][1]
        floor = 6 * cycles + 2 * fetches
        assert floor <= clock - points["begin"][0]
        result[name] = dict(cpu_cycles=cycles, min_WRAM_fetches=fetches,
                            instructions=count, path_signature=signature, min_clocks=floor)
    return result


def inspect(temp, phase):
    view = {}
    for paired, name in ((False, "978"), (True, "998pair")):
        d, commands, packets = releases(temp, phase, paired)
        view[name] = dict(trace_hash=sha(d / "window.csv"), packets=packets)
    first = next(r for r in rows(d / "budget685.csv") if r["generation"] == "907")
    cutoff = int(first["latch_clock"]) + (247 - int(first["line"])) * 1364 - int(first["h"])
    audit = [seal_floor(temp / f"nes-ready999-pair-{mode}-p{phase}-audit")
             for mode in ("instant", "busy")]
    assert audit[0] == audit[1]
    # Grant free, immediately available tiles and a free BEGIN. All remaining
    # E1 transactions share a wire. No release order within the suffix is assumed.
    ordinary = [r for r in packets[:-1] if r["op"] not in (1, 7)]
    def suffix(at):
        return [r for r in ordinary if r["src"] >= at] + packets[-1:]
    def finish(at):
        return at + sum(r["wire_B"] for r in suffix(at)) * 8 * MASTER / 2_625_000
    at = max({r["src"] for r in ordinary}, key=finish)
    e1 = math.floor(finish(at))
    # Round down and allow an additional 64 clocks for callback boundaries.
    guard = 64
    dma = (512 + 544) * 8
    lower = e1 + audit[0]["upload"]["min_clocks"] + dma - guard
    assert lower > cutoff
    view["bound"] = dict(cutoff=cutoff, suffix_start=at, E1_wire_B=sum(r["wire_B"] for r in suffix(at)),
                         packet_indices=[r["index"] for r in suffix(at)], E1_end_floor=e1,
                         seal_path=audit[0], final_DMA_min=dma, guard=guard,
                         missed_ms=round((lower - cutoff) * 1000 / MASTER, 6))
    view["replays"] = {}
    for mode in ("instant", "paid", "joined", "busy"):
        out = temp / f"nes-ready999-pair-{mode}-p{phase}"
        view["replays"][mode] = counters(out)
        assert sha(out/"frame-907.rgb") == sha(d/"frame-907.rgb")
    guards = {}
    for fault, status in (("bad_seal", 224), ("stop_decode", 228)):
        out = temp / f"nes-ready999-pair-paid-p{phase}-{fault}"
        result = read(out/"result.json")
        assert result["passed"] and (result["commits"],result["last_status"]) == (2,status)
        assert sha(out/"retained.rgb") == sha(d/"frame-906.rgb")
        guards[fault] = status
    view["guards"] = guards
    baseline = directory(temp,phase,"978returned","cold")
    view["screen"] = {g: counters(temp / f"nes-ready999-screen-{g}-{mode}-p{phase}",g)
                      for g, mode in ((909,"frame"), (910,"prelude"), (912,"frame"))}
    view["bank912"] = {"978": counters(baseline,912)}
    for advance in (0,2,4):
        out = temp / f"nes-ready999-bank-{advance}-p{phase}"
        assert all(sha(out/f"frame-{g}.rgb")==sha(baseline/f"frame-{g}.rgb") for g in range(905,913))
        w = [r for r in rows(out/"window.csv") if r["g"]=="912" and r["op"]=="3"]
        result = counters(out,912)
        result["dma"] = [[int(r[k]) for k in ("value","clock","frame","line")] for r in w if r["event"]=="ppu_dma"]
        result["wait"] = [[r["event"],int(r["clock"])] for r in w if r["event"] in ("wait169","wait_return_5781")]
        view["bank912"][str(advance)] = result
    assert view["bank912"]["0"] == view["bank912"]["2"] == view["bank912"]["4"]
    return view


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    data = {p: inspect(args.temp,p) for p in (1,2)}
    args.output.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
