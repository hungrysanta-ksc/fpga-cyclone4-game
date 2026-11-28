"""Decode the fixed 5.5 s Dragon Quest IV movement window and match repeats."""
import argparse
import json
from pathlib import Path
from statistics import mean
from struct import Struct
from compare_ff3_movement1052 import HEADER, TICK_MS, dt, summary

ROW = Struct("<IHH11sBH")
WINDOW_MS = 5500


def decode(data):
    magic, edition, slot, rom, serial, crc, used, _, done, misses = HEADER.unpack_from(data)
    if (magic, edition, slot, rom) != (0x31364d44, 1061, 1, 0x9ac62bb9):
        raise ValueError("requires a DQ4 slot 1 restore")
    if done != 1 or misses or not 3 <= used <= 340 or len(data) < HEADER.size + used * ROW.size:
        raise ValueError(f"incomplete or interrupted recording: rows={used}, status={done}, missing={misses}")
    rows = []
    for i in range(1, used):
        ack, x, y, p, dirty, tiles = ROW.unpack_from(data, HEADER.size + i * ROW.size)
        flags = p[2]
        if not flags & 16:
            raise ValueError("direction trigger was lost")
        move = p[9] | ((p[10] & 15) << 8)
        show = p[5] | ((p[8] & 15) << 8)
        if not rows:
            at = (((show - move + 2048) % 4096) - 2048) * TICK_MS
            if at < -20:
                raise ValueError("ambiguous first publication")
        else:
            prev = rows[-1]
            gap = dt(show, prev["show"])
            ack_gap = ((ack - prev["arm_ack"]) & 0xffffffff) / 84000
            if move != prev["move"] or gap <= 0 or abs(ack_gap - gap) > 10:
                raise ValueError("inconsistent FPGA/ARM timestamps")
            at = prev["at_ms"] + gap
        rows.append(dict(index=i, at_ms=at, gen=int.from_bytes(p[:2], "little"), x=x, y=y,
                         direction=flags & 15, arm_ack=ack, move=move, show=show, dirty=dirty,
                         tile_bytes=tiles, tile=(p[3] | ((p[7] & 15) << 8)) if flags & 32 else None,
                         seal=p[4] | ((p[7] >> 4) << 8), final=p[6] | ((p[8] >> 4) << 8)))
    if rows[-1]["at_ms"] < WINDOW_MS:
        raise ValueError("recording ended before the fixed window")
    return (rom, slot, serial, crc), [r for r in rows if 0 <= r["at_ms"] < WINDOW_MS]


def analyze(paths):
    result, bins, identity = {}, [], None
    for path in paths:
        key, rows = decode(path.read_bytes())
        if identity is not None and identity != key:
            raise ValueError("different restored journal identities")
        identity = key
        stats = summary(rows)
        stats["fixed_window_fps"] = round(len(rows) * 1000 / WINDOW_MS, 3)
        result[str(path)] = stats
        groups = {}
        for a, b in zip(rows, rows[1:]):
            pos = (b["x"], b["y"], b["direction"], b["dirty"], b["tile_bytes"])
            groups.setdefault(pos, []).append(b["at_ms"] - a["at_ms"])
        bins.append(groups)
    matched = set.intersection(*(set(b) for b in bins))
    return dict(identity=identity, runs=result, common_workload_positions=len(matched),
                equal_weight_gap_ms=[round(mean(mean(b[k]) for k in matched), 3) for b in bins] if matched else [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recordings", type=Path, nargs="+")
    print(json.dumps(analyze(parser.parse_args().recordings), indent=2))
