"""Locate the first observable delay in the two physical MMC1014 tile traces."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from read_nes_tail1012 import ARM_TICK, MS, OFFSET, STRIDE, TRACE, decode

ROOT = Path(__file__).resolve().parents[1]


def analyze(directory, record):
    edition = record["edition"]
    trial = record["trial"]
    path = directory / f"nes-frame-mmc{edition}-{trial}차.bin"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != record["sha256"]["frame"]:
        raise ValueError(f"Unexpected trial log: {path.name}")
    trace = decode(raw, edition)
    candidates = []
    for row in trace["rows"]:
        if "invalid" in row:
            raise ValueError("Invalid display record")
        ready, kind, size, offset, gen, token = struct.unpack("<BBHHHI", bytes.fromhex(row["descriptor_hex"]))
        if (5900 <= row["tick"] < 6000 and
                (row["BG"], row["OBJ"], row["map"], row["tiles"], row["chunks"]) == (521, 17, 23, 15, 3) and
                (ready, kind, size, offset, gen) == (1, 1, 64, 480, row["generation"])):
            candidates.append((row, token))
    (row, token), = candidates
    if any(trace["dropped"]):
        raise ValueError("Incomplete capture")
    # Recover on the FPGA clock only. decode() already rejects ambiguous age wraps.
    base = row["previous_show"]
    publish = row["show"] - round(row["last_tile_to_show_ms"] / MS)
    e9 = publish - round(row["supply_ms"] / MS)
    events = dict(previous_show=base, first_E9=e9, last_tile_publish=publish, SEAL=row["SEAL"],
                  last_DMA=row["last_DMA"], show=row["show"], final_ACK=row["final_ACK"])
    if list(events.values()) != sorted(events.values()):
        raise ValueError("Reconstructed events out of order")
    times = list(events.values())
    stages = dict(zip(("previous_show_to_E9", "E9_to_publish", "publish_to_SEAL",
                       "SEAL_to_last_DMA", "last_DMA_to_show", "show_to_final_ACK"),
                      (b-a for a, b in zip(times, times[1:]))))
    if sum(stages.values()) != row["final_ACK"] - base:
        raise ValueError("Intervals do not reconcile to the final ACK")
    selected = [s["generation"] for s in trace["samples"]]
    scratch_gen = TRACE.unpack_from(raw, OFFSET+2*STRIDE)[1]
    if row["generation"] in (*selected, scratch_gen):
        raise ValueError("Target has an ARM packet trace; inspect it before drawing conclusions")
    return dict(edition=edition, trial=trial, log_sha256=digest, generation=row["generation"],
                frame_start_tick=row["tick"], output_bank=row["bank"], last_OBJ_token=token,
                stored_ARM_packet_generations=selected, scratch_generation=scratch_gen,
                FPGA_event_ticks=events, interval_ticks=stages,
                interval_ms={k:round(v*MS, 4) for k,v in stages.items()},
                measured_final_ACK_to_ARM_E0_ms=row["final_ACK_to_ARM_E0_ms"])


def report(directory):
    archive = json.loads((ROOT/"analysis/tail1014-hardware.json").read_bytes())
    runs = [analyze(directory, record) for record in archive["runs"]]
    first, second = [r for r in runs if r["edition"] == 1014]
    if (first["generation"], second["generation"]) != (1489, 1384):
        raise ValueError("Different physical pair")
    delta = {k:round((second["interval_ticks"][k]-v)*MS, 4) for k,v in first["interval_ticks"].items()}
    return dict(FPGA_tick_ms=MS, ARM_tick_ms=ARM_TICK, reference_edition=1012, runs=runs,
                second_minus_first_ms=delta,
                unavailable_per_generation=["tile CHR tag and cache hit", "ROM request, grant and owner",
                                            "bank return timestamps for the three tokens"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(report(args.directory), indent=2)+"\n", encoding="utf8")
