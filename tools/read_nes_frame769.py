"""Decode paired 25–30 s frame records and budget from MMC770/771/772."""
import argparse
import csv
import struct
import sys
from pathlib import Path

REASONS = ("E0_room", "E0_credit", "E0_pending", "E0_final", "E0_drained",
           "E8_flush", "E8_finish", "E8_retire", "E8_rearm")
ROW = struct.Struct("<4H28B")


def decode(data, budget):
    fields = dict(line.split("=", 1) for line in budget.splitlines() if "=" in line)
    if fields.get("frame769") != "1" or fields.get("tick_ms") != "10":
        raise ValueError("unsupported budget")
    count = int(fields["rows"])
    if not 0 <= count <= 8192//ROW.size or len(data) != ROW.size * count:
        raise ValueError("row count or file length mismatch")
    previous = None
    last_tick = 0
    for record in ROW.iter_unpack(data):
        tick, gen, obj, bg, dirty, flags, seal, dma, ack = record[:9]
        if not 2500 <= tick < 3000 or tick < last_tick or flags & ~3:
            raise ValueError("invalid frame header")
        last_tick = tick
        valid = bool(flags & 1)
        row = dict(start_tick=tick, generation=gen, map_groups=dirty, obj=obj, bg=bg,
                   valid=valid, saturated=bool(flags & 2), dropped_window=int(fields["dropped"]),
                   seal_vb=seal if valid else "", dma_vb=dma if valid else "", ack_vb=ack if valid else "",
                   seal_to_dma_vb=(dma-seal)%256 if valid else "",
                   dma_to_ack_vb=(ack-dma)%256 if valid else "",
                   ack_interval_vb=(ack-previous)%256 if valid and previous is not None else "")
        e0, e0_changes, e8, e8_ready = record[28:32]
        if e0_changes > e0 or e8_ready > e8:
            raise ValueError("invalid output counters")
        row.update(output_E0=e0, output_E0_quiet=e0-e0_changes, output_E8=e8, output_E8_ready=e8_ready)
        previous = ack if valid else None
        for i, name in enumerate(REASONS):
            total, positive = record[9+i], record[18+i]
            if positive > total:
                raise ValueError("progress count exceeds calls")
            row[name] = total
            row[name + ("_quiet" if i < 5 else "_ready")] = total-positive if i < 5 else positive
        yield row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("budget", type=Path)
    args = parser.parse_args()
    rows = list(decode(args.binary.read_bytes(), args.budget.read_text(encoding="utf-8-sig")))
    if rows:
        writer = csv.DictWriter(sys.stdout, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
