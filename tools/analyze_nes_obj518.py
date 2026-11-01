# SPDX-License-Identifier: MIT
"""Join validated ARM/65816 completions, NES reference states and per-generation plan demand."""
import argparse
import csv
import json
from pathlib import Path

from check_nes_game478 import sha

MASTER_HZ = 21477272


def analyze(a):
    def read(path):
        return json.loads(path.read_text(encoding="utf8"))

    windows, plans = read(a.windows), read(a.profile)
    reference = read(a.reference / "reference.json")
    candidate, original = [read(d / "joint.json") for d in (a.joint, a.original)]
    assert reference["matched_PPU_states_and_clocks"] == 71
    assert reference["trace_SHA256"] == sha(a.reference / "positions.csv")
    assert windows["firmware_SHA256"] == plans["firmware_sha256"] == candidate["firmware_SHA256"]
    assert candidate["passed"] and original["passed"]
    assert candidate["parameters"] == original["parameters"] and candidate["client_SHA256"] == original["client_SHA256"]
    assert candidate["map_WRAM_VRAM_verified"] == original["map_WRAM_VRAM_verified"] == 12
    phases = read(a.joint / "obj-phases.json")
    with (a.joint / "window.csv").open() as f:
        trace = list(csv.DictReader(f))
    frames = []
    assert len(candidate["frames"]) == len(original["frames"]) == 12
    for c, o, demand in zip(candidate["frames"], original["frames"], plans["frames"]):
        g = c["generation"]
        assert g == demand["generation"] == o["generation"]
        image = f"frame-{g}.rgb"
        assert sha(a.joint / image) == sha(a.original / image)
        phase = phases[str(g)]
        rows = [r for r in trace if int(r["g"]) == g]
        final = [r for r in rows if r["op"] == "3" and r["event"] == "ack"]
        assert len(final) == 1 and final[0]["value"] == "1" and int(final[0]["clock"]) == c["ACK_masterclock"]
        obj_acks = [int(r["clock"]) for r in rows if r["op"] == "7" and r["section"] == "1" and r["event"] == "ack"]
        assert len(phase.get("obj_plans", [])) == demand["obj_tiles"]
        assert phase.get("obj_rom_reads", 0) == demand["obj_rom_bytes_requested"]
        assert phase["end_accepted"] <= c["ACK_masterclock"] <= phase["ea"]
        frames.append(dict(generation=g, obj_tiles=demand["obj_tiles"], last_obj_rom_response=phase.get("last_obj_rom_response"),
                           last_obj_bulk_ack=max(obj_acks, default=None), end_accepted=phase["end_accepted"],
                           seal_entered=int(next(r["clock"] for r in rows if r["op"] == "3" and r["event"] == "seal")),
                           final_ready=c["final_ready_masterclock"], display_ack=c["ACK_masterclock"], ea=phase["ea"],
                           original_display_ack=o["ACK_masterclock"]))
    def warm_interval(field):
        return (frames[-1][field] - frames[1][field]) / 10 * 1000 / MASTER_HZ

    return dict(scope="Fixed inputs, linked ARM and 65816, repeated boot ROM-grant calendar; not a hardware FPS run.",
                windows=windows, reference=reference, plans=plans, matched_schedule=frames,
                warm_reference_ms=warm_interval("original_display_ack"), warm_candidate_ms=warm_interval("display_ack"),
                hashes={f"{side}_{name}":sha(d / name) for side, d in (("reference", a.original), ("candidate", a.joint))
                        for name in ("joint.json", "window.csv", "events.json")})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("windows", "profile", "reference", "joint", "original", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    result = analyze(a)
    a.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8", newline="\n")
