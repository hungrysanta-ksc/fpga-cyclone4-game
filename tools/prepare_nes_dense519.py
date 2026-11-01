# SPDX-License-Identifier: MIT
"""Prepare private, contiguous SMB3 inputs and the first-OBJ publication experiment."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from nes_raw506 import once
from run_nes_scroll229 import ROM_SHA, sha
from test_nes_schedule496 import prepare

ROOT = Path(__file__).resolve().parents[1]


def tiles(folder, last):
    """Canonical tile payloads, independent of packet grouping and ordinals."""
    blob = (folder / "requests.bin").read_bytes()
    at = index = 0
    result = {}
    while at < len(blob):
        n, = struct.unpack_from("<H", blob, at)
        record = blob[at + 2:at + 2 + n]
        assert len(record) == n and n >= 16
        at += n + 2
        index += 1
        if record[0] != 7:
            continue
        g, offset = struct.unpack_from("<HH", record, 8)
        if g > last:
            continue
        payload = (folder / f"tile-{index:04d}.bin").read_bytes()
        size = 32 if record[1] else 16
        assert len(payload) == int.from_bytes(record[14:16], "little") and len(payload) % size == 0
        for i in range(0, len(payload), size):
            key = (g, record[1], offset + i)
            assert key not in result
            result[key] = payload[i:i + size]
    return result


def tile_digest(records):
    digest = hashlib.sha256()
    for (generation, kind, offset), payload in sorted(records.items()):
        digest.update(struct.pack("<HBH", generation, kind, offset))
        digest.update(payload)
    return digest.hexdigest()


def verify(args):
    assert sha(args.rom) == ROM_SHA
    for g in range(905, 958):
        hdma = (args.out / f"expected-{g}.bin").read_bytes()
        assert hdma == (args.capture / f"frame{g}/expected-hdma.bin").read_bytes()
        if g <= 916:
            assert hdma == (args.prefix / f"expected-{g}.bin").read_bytes()
    prefix = tiles(args.prefix, 916)
    assert len(prefix) == 219 and prefix == tiles(args.out, 916)
    all_tiles = tiles(args.out, 957)
    return {"canonical_tile_sha256": tile_digest(all_tiles), "tiles": len(all_tiles), "frames": 53, "prefix_tiles": len(prefix), "ROM_sha256": ROM_SHA,
            "request_fixture_sha256": sha(args.out / "requests.bin")}


def patch(args):
    expected = json.loads((ROOT / "analysis/obj518-verification.json").read_text())
    assert sha(args.arm / "obj-nes-100/firmware.stm") == expected["windows"]["firmware_SHA256"]
    name = "nes_plan_service200.c"
    text = once((args.arm / name).read_text(), "if(!p->early&&q->kind==0)", "if(!p->early&&q->kind<2)")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / name).write_text(text, encoding="utf8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    arm = commands.add_parser("patch")
    for key in ("arm", "out"):
        arm.add_argument("--" + key, type=Path, required=True)
    for mode in ("fixture", "verify"):
        cmd = commands.add_parser(mode)
        for key in ("compact", "capture", "prefix", "rom", "out"):
            cmd.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    if args.action == "patch":
        patch(args)
    else:
        assert sha(args.rom) == ROM_SHA
        if args.action == "fixture":
            args.out.mkdir(parents=True, exist_ok=False)
            args.frames, args.row_counts = 53, None
            prepare(args, args.out, True)
        print(json.dumps(verify(args)))
