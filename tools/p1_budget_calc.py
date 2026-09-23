"""Read-only, reproducible lower-bound arithmetic for SYSTEM-BUDGET.ko.md.

Uses frozen JSON/fit reports from an explicitly supplied private local snapshot.
No ROM, tool, simulation, synthesis, or network access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = {
    "nominal": "g13-endpoint-startup-prefill10-v1-nominal",
    "dense_phase0": "g13-endpoint-startup-prefill10-phase0-v1-dense",
    "dense_phase700000": "g13-endpoint-startup-prefill10-phase700000-line229-v1-dense",
    "first_dma_gaps": "g13-endpoint-first-gaps-prefill10-phase0-v1-dense",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True,
                        help="Private local snapshot containing probes/full-core-link/results")
    args = parser.parse_args()
    results = args.snapshot.resolve() / "probes" / "full-core-link" / "results"
    candidate = results / "fxpak-g13-prefill-endpoint-seed7-hold1-v1"
    if not candidate.is_dir():
        parser.error("candidate reports not found beneath --snapshot")
    source_hz = 8_000_000 * 151 / 36
    bus_hz = 84_000_000
    frame_cycles = 561_792
    frame_s = frame_cycles / source_hz
    data = {key: json.loads((results / path / "verification.json").read_text(encoding="utf-8"))
            for key, path in CASES.items()}
    bytes_per_frame = data["nominal"]["metrics"]["bytes"] / data["nominal"]["frames"]
    if bytes_per_frame != 21_764:
        raise ValueError("Unexpected output bytes/frame")
    if any(x["metrics"]["bytes"] / x["frames"] != bytes_per_frame for x in data.values()):
        raise ValueError("Cases have different byte counts")
    if bytes_per_frame % 2:
        raise ValueError("Word-only output needs an even byte count")
    pages = (candidate / "frame_output_pages.sv").read_text(encoding="utf-8")
    writer = (candidate / "sram_burst_writer.sv").read_text(encoding="utf-8")
    if "assign byte_valid=0" not in pages or "word (14 clocks)" not in writer:
        raise ValueError("Output transaction mode changed; revise writer budget")
    writer_bus_cycles = int(bytes_per_frame / 2 * 14)

    fit = (candidate / "pin.fit.rpt").read_text(encoding="utf-8", errors="replace")
    memory = []
    for line in fit.splitlines():
        if not line.startswith("; full_core_link:"):
            continue
        c = [item.strip() for item in line.split(";")]
        if len(c) < 24 or not c[19].isdigit():
            continue
        memory.append({"hierarchy": c[1].split("|altsyncram:")[0],
                       "depth": int(c[5]), "width": int(c[6]),
                       "bits": int(c[18]), "m9k": int(c[19]),
                       "clock_mode": c[4], "port_a_rdw": c[23]})
    if len(memory) != 8 or sum(x["m9k"] for x in memory) != 56:
        raise ValueError("Fit memory map changed")

    cases = {}
    for name, record in data.items():
        cycles = record["metrics"]["max_cycles"]
        cases[name] = {
            "max_processing_cycles": cycles,
            "frame_budget_cycles": frame_cycles,
            "excess_cycles": cycles - frame_cycles,
            "max_to_frame_ratio": round(cycles / frame_cycles, 6),
            "fifo_peak": record["metrics"]["fifo_peak"],
            "commits": record["metrics"]["commits"],
            "published": record["metrics"]["published"],
            "observed_frames": record["frames"],
        }
    result = {
        "scope": "read-only arithmetic, not sustained throughput or physical bus signoff",
        "source_hz": round(source_hz, 6),
        "bus_hz": bus_hz,
        "source_frame_cycles": frame_cycles,
        "source_frame_ms": round(frame_s * 1000, 6),
        "source_frames_per_s": round(1 / frame_s, 6),
        "output_bytes_per_frame": bytes_per_frame,
        "minimum_average_output_bytes_per_s": round(bytes_per_frame / frame_s, 3),
        "ideal_writer_mode": "word-only; 14 bus clocks per adjacent 2-byte transaction",
        "ideal_writer_bus_cycles_per_frame": writer_bus_cycles,
        "ideal_writer_bus_ms_per_frame": round(writer_bus_cycles / bus_hz * 1000, 6),
        "ideal_writer_bus_fraction": round(writer_bus_cycles / bus_hz / frame_s, 6),
        "cases": cases,
        "fit_memory": memory,
        "fit_memory_bits": sum(x["bits"] for x in memory),
        "fit_m9k_blocks": sum(x["m9k"] for x in memory),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
