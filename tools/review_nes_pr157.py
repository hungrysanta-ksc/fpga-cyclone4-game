"""Compare the archived PR157 entry and exit replay on matching source and output."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

MASTER_HZ = 21_477_272.727
SPI_HZ = 2_625_000


def read_run(directory):
    joint = json.loads((directory / "joint.json").read_bytes())
    assert joint["passed"] and joint["commits"] == 53 and joint["last_status"] == 1
    with (directory / "window.csv").open(newline="") as stream:
        reveals = {int(row["g"]): row for row in csv.DictReader(stream)
                   if row["event"] == "reveal"}
    assert set(reveals) == set(range(905, 958))
    start, end = (int(reveals[g]["clock"]) for g in (951, 957))
    transactions = [e for e in json.loads((directory / "events.json").read_bytes())
                    if e["event"] == "SPI" and start <= e["start"] and e["clock"] <= end]
    assert all(x["clock"] <= y["start"] for x, y in zip(transactions, transactions[1:]))
    wire = Counter()
    for event in transactions:
        wire[event["opcode"]] += event["bytes"]
    data = [e for e in transactions if e["opcode"] in ("0xd1", "0xe1")]
    intervals = {g: int(reveals[g]["frame"]) - int(reveals[g - 1]["frame"])
                 for g in range(906, 958)}
    files = ["window.csv", "events.json", "joint.json"]
    assert joint["frames"][-1]["generation"] == 957
    return {
        "directory": directory.name,
        "sha256": {f: hashlib.sha256((directory / f).read_bytes()).hexdigest() for f in files},
        "start": joint["parameters"]["start"], "ROM_calendar": joint["parameters"]["ROM_calendar"]["trace_SHA256"],
        "intervals_VBlank": intervals, "total_intervals_VBlank": sum(intervals.values()),
        "dense_reveal_clocks": [start, end], "dense_mean_ms": (end - start) * 1000 / MASTER_HZ / 6,
        "final_ACK": joint["frames"][-1]["ACK_masterclock"], "dense_SPI_B": dict(sorted(wire.items())),
        "dense_SPI_transactions": len(transactions), "dense_SPI_B_total": sum(wire.values()),
        "dense_SPI_wire_only_ms": sum(wire.values()) * 8000 / SPI_HZ,
        "dense_SPI_transaction_ms": sum(e["clock"] - e["start"] for e in transactions) * 1000 / MASTER_HZ,
        "dense_D1_E1_transactions": len(data), "dense_D1_E1_B": sum(e["bytes"] for e in data),
        "dense_D1_E1_transaction_ms": sum(e["clock"] - e["start"] for e in data) * 1000 / MASTER_HZ,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_root", type=Path)
    args = parser.parse_args()
    result = {"target_six_frames_ms": 100, "master_Hz": MASTER_HZ, "SPI_Hz": SPI_HZ, "phases": []}
    for phase in (1, 2):
        entry, exit_run = [args.trace_root / f"{name}{phase}" for name in ("nes-bg707-step", "nes-credit753-prefix")]
        before, after = read_run(entry), read_run(exit_run)
        assert before["start"] == after["start"] and before["ROM_calendar"] == after["ROM_calendar"]
        matches = {}
        for pattern in ("map-{}.bin", "expected-{}.bin", "frame-{}.rgb"):
            count = sum((entry / pattern.format(g)).read_bytes() == (exit_run / pattern.format(g)).read_bytes()
                        for g in range(905, 958))
            assert count == 53
            matches[pattern] = count
        result["phases"].append({"phase": phase, "matching_files": matches, "entry": before, "exit": after,
                                 "final_ACK_saved_ms": (before["final_ACK"] - after["final_ACK"]) * 1000 / MASTER_HZ})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
