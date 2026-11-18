"""Compare bus occupancy between the second and sixth reveals of the demo clip."""
import json
from collections import defaultdict
from pathlib import Path

from analyze_nes_section841 import folder, window


def budget(phase, tag):
    run = folder(phase, tag)
    assert json.loads((run / "joint.json").read_bytes())["passed"]
    reveals = [r for r in window(run) if r["event"] == "reveal"]
    assert [r["g"] for r in reveals] == list(range(905, 911))
    start, end = reveals[1]["clock"], reveals[-1]["clock"]
    ticks = defaultdict(float)
    whole_bytes = defaultdict(int)
    previous = 0
    for event in json.loads((run / "events.json").read_bytes()):
        if event["event"] != "SPI":
            continue
        begin, finish = event["start"], event["clock"]
        assert previous <= begin + 0.01 and begin <= finish
        previous = finish
        overlap = min(finish, end) - max(begin, start)
        if overlap > 0:
            ticks[event["opcode"]] += overlap
            if start <= begin and finish <= end:
                whole_bytes[event["opcode"]] += event["bytes"]
    clocks_per_ms = 236250000 / 11 / 1000
    data_bytes = sum(whole_bytes[k] for k in ("0xd1", "0xe1"))
    return dict(reveal_clocks=[r["clock"] for r in reveals[1:]],
                vblank_gaps=[b["frame"] - a["frame"] for a,b in zip(reveals[1:], reveals[2:])],
                SPI_ms=round(sum(ticks.values()) / clocks_per_ms, 3),
                opcode_ms={k: round(v / clocks_per_ms, 3) for k,v in ticks.items()},
                complete_transaction_bytes=dict(whole_bytes),
                D1_E1_min_wire_ms=round(data_bytes * 8 / 2625000 * 1000, 3))


if __name__ == "__main__":
    result = {name: [budget(p, tag) for p in (1, 2)] for name, tag in
              (("MMC826", "832base"), ("sim837", "837client-stickypalette"))}
    result["scope"] = ("Four elapsed display intervals, sampled source frames. "
                       "Boundary transactions clipped for occupancy and excluded from byte counts. "
                       "Driver and ROM schedule modeled. Not a consecutive-source 60 Hz workload.")
    Path("analysis/pr166-bus-budget.json").write_text(json.dumps(result, indent=2)+"\n", newline="\n")
