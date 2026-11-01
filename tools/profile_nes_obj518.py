# SPDX-License-Identifier: MIT
"""Profile tile plans from the linked ARM planner on the pinned 71-frame SMB3 capture."""
import argparse
import json
import re
import struct
from pathlib import Path

from check_nes_game478 import Machine, sha
from nes_transfer512 import legacy_packets


def profile(a):
    sealed = json.loads((a.data / "result.json").read_text())
    assert sealed["passed"]
    colors = re.search(r"\{(.*?)\}", (a.arm / "nes_palette165.inc").read_text(), re.S)[1]
    m = Machine(a.arm, struct.pack("<64H", *map(int, colors.split(","))))
    frames = []
    for g in range(905, 976):
        files = [a.data / f"frame{g}.{ext}" for ext in ("geometry", "raw")]
        for f in files:
            assert sha(f) == sealed["evidence_files"][f.name]
        geometry, raw = [f.read_bytes() for f in files]
        blocks, _, _ = legacy_packets(geometry, raw, g)
        frame = m.frame(blocks, geometry, raw, g, g - 904)
        if g <= 916:
            assert frame["plans"] == json.loads((a.plans / f"frame{g}/plans.json").read_text()), g
        obj, bg, reads = 0, 0, 0
        for bank, record in frame["plans"]:
            gen, _, _, kind, mask = struct.unpack_from("<HHHBB", bytes.fromhex(record))
            assert gen == g and bank == frame["bank"] and kind in (0, 1, 2)
            if kind == 1:
                obj += 1
                reads += 2 * mask.bit_count()
            elif kind == 0:
                bg += 1
        frames.append(dict(generation=g, obj_tiles=obj, bg_tiles=bg, obj_rom_bytes_requested=reads))
    return dict(firmware_sha256=sha(a.arm / "obj-nes-100/firmware.stm"), frames=frames,
                verified_joint_plan_frames=12, scope="Planner demand. No ROM service or display timing inferred.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("arm", "data", "plans", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    with a.out.open("x", encoding="utf8") as f:
        json.dump(profile(a), f, indent=2)
        f.write("\n")
