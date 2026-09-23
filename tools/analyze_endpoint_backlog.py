"""Summarize a private G13 endpoint log without copying the raw log into Git.

The two clocks and source period must come from the testbench being analyzed.
This computes model timing proxies; it does not infer physical bus timing.
"""

import argparse
import json
import re
import statistics
from pathlib import Path


FIELDS = re.compile(r"([a-z_]+)=(-?\d+)")


def fields(line):
    return {key: int(value) for key, value in FIELDS.findall(line)}


def analyze(log, source_frame_cycles, source_clock_ns, host_clock_ns):
    starts = {}
    frame_cycles = {}
    stalls = {}
    installs = []
    visibles = []
    final = {}
    for line in log.splitlines():
        if "STALL_PROFILE frame=" in line:
            item = fields(line)
            starts[item["frame"]] = item["start_cycle"]
            stalls[item["frame"]] = item
        elif "FRAME_DATA_PASS frame=" in line:
            item = fields(line)
            frame_cycles[item["frame"]] = item["cycles"]
        elif "HOST_EVENT kind=" in line:
            item = fields(line)
            if item["kind"] == 6:
                installs.append(item)
            elif item["kind"] == 7:
                visibles.append(item)
        elif "ENDPOINT_PASS commits=" in line:
            final["endpoint"] = fields(line)
        elif "HOST_PASS installs=" in line:
            final["host"] = fields(line)
        elif "DIAGNOSTIC_ONLY deadline_misses=" in line:
            final["diagnostic"] = fields(line)
        elif re.search(r"\*\* (?:Error|Fatal)\b|FATAL", line):
            raise ValueError("Simulator error in log")

    count = len(frame_cycles)
    if count == 0 or sorted(frame_cycles) != list(range(count)):
        raise ValueError("Missing or noncontiguous frame records")
    if sorted(starts) != list(range(count)):
        raise ValueError("Missing or noncontiguous start records")
    if any(stalls[i]["end_cycle"] - starts[i] != frame_cycles[i] for i in range(count)):
        raise ValueError("Start/end and frame duration disagree")
    if final.get("endpoint", {}).get("commits") != count or final["endpoint"].get("published") != count:
        raise ValueError("Missing or inconsistent endpoint completion")
    if final.get("host", {}).get("installs") != len(installs):
        raise ValueError("Missing or inconsistent host completion")
    if final["host"].get("consumed") != count - 1:
        raise ValueError("Host did not consume the last source epoch")
    if final.get("diagnostic", {}).get("deadline_misses") != sum(
        cycles >= source_frame_cycles for cycles in frame_cycles.values()
    ):
        raise ValueError("Deadline count disagrees with frame records")

    epochs = [event["epoch"] for event in installs]
    if epochs[0] != 0 or epochs[-1] != count - 1 or any(
        following not in (prior, prior + 1) for prior, following in zip(epochs, epochs[1:])
    ):
        raise ValueError("Installed epoch skipped or reversed")
    repeat_epochs = [epoch for epoch in range(count) if epochs.count(epoch) > 1]
    first_install = {}
    for event in installs:
        first_install.setdefault(event["epoch"], event)
    first_visible = {}
    for event in visibles:
        first_visible.setdefault(event["epoch"], event)
    if any(epoch not in first_install for epoch in range(count)):
        raise ValueError("Missing source epoch installation")

    drift = [starts[i] - starts[0] - i * source_frame_cycles for i in range(count)]
    complete_to_install_ms = [
        (first_install[i]["bus_cycle"] * host_clock_ns -
         (starts[i] + frame_cycles[i]) * source_clock_ns) / 1_000_000
        for i in range(count)
    ]
    start_to_visible_ms = [
        (first_visible[i]["bus_cycle"] * host_clock_ns - starts[i] * source_clock_ns) / 1_000_000
        for i in sorted(first_visible)
        if i in starts
    ]
    return {
        "scope": "synthetic host and source; age starts at pipeline processing, not original GBC capture",
        "frames": count,
        "source_frame_cycles": source_frame_cycles,
        "deadline_misses": final["diagnostic"]["deadline_misses"],
        "worst_frame_cycles": max(frame_cycles.values()),
        "steady_frames": count - 4,
        "steady_median_cycles_after_frame_3": statistics.median(frame_cycles[i] for i in range(4, count)) if count > 4 else None,
        "start_drift_from_frame_0_cycles": {
            "max": max(drift), "max_frame": drift.index(max(drift)), "last": drift[-1]
        },
        "host_installs": len(installs),
        "repeat_epochs": repeat_epochs,
        "first_install_after_completion_ms": {
            "min": round(min(complete_to_install_ms), 3),
            "max": round(max(complete_to_install_ms), 3),
        },
        "first_visible_from_pipeline_start_ms": {
            "observed_epochs": len(start_to_visible_ms),
            "min": round(min(start_to_visible_ms), 3),
            "max": round(max(start_to_visible_ms), 3),
        } if start_to_visible_ms else None,
        "stall_outliers": [
            {key: stalls[i][key] for key in ("frame", "pix_fifo", "pix_dma", "pal_page", "pal_fifo", "pal_dma")}
            for i in range(count) if frame_cycles[i] >= source_frame_cycles
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--source-frame-cycles", type=int, required=True)
    parser.add_argument("--source-clock-ns", type=float, required=True)
    parser.add_argument("--host-clock-ns", type=float, required=True)
    args = parser.parse_args()
    if args.source_frame_cycles <= 0 or args.source_clock_ns <= 0 or args.host_clock_ns <= 0:
        parser.error("Clock periods and source frame length must be positive")
    print(json.dumps(analyze(args.log.read_text(errors="replace"), args.source_frame_cycles,
                             args.source_clock_ns, args.host_clock_ns), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
