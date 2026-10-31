# SPDX-License-Identifier: MIT
"""Capture original MMC509 map writes and independent planner images."""
import argparse
import json
import re
import struct
from pathlib import Path

from audit_nes_output489 import CompactAudit
from check_nes_game478 import sha
from nes_transfer512 import legacy_packets
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2

ROOT = Path(__file__).resolve().parents[1]


def measure(arm, data, out):
    out.mkdir(parents=True, exist_ok=False)
    evidence = json.loads((ROOT / "analysis/transfer512-verification.json").read_text())
    assert sha(arm / "obj-nes-100/firmware.stm") == evidence["variants"]["original"]["firmware_SHA256"]
    sealed = json.loads((data / "result.json").read_text())
    assert sealed["passed"]
    palette = re.search(r"\{(.*?)\}", (arm / "nes_palette165.inc").read_text(), re.S)[1]
    machine = CompactAudit(arm, struct.pack("<64H", *map(int, palette.split(","))), out)
    map_at = machine.video + machine.layout["nes_native_video165"]["map"]
    touched_words = set()

    def observe_write(uc, access, address, size, value, user):
        old = bytes(uc.mem_read(address, size))
        new = value.to_bytes(size, "little", signed=value < 0)
        for i, (before, after) in enumerate(zip(old, new)):
            if before != after and map_at <= address + i < map_at + 4096:
                touched_words.add((address + i - map_at) // 2)

    machine.u.hook_add(UC_HOOK_MEM_WRITE, observe_write, begin=map_at, end=map_at+4095)
    changed_calls = []

    def observe_word(uc, address, size, user):
        assert uc.reg_read(UC_ARM_REG_R0) == machine.video
        byte_at = uc.reg_read(UC_ARM_REG_R1)
        assert byte_at % 2 == 0 and 0 <= byte_at < 4096
        value = uc.reg_read(UC_ARM_REG_R2) & 0xffff
        if int.from_bytes(uc.mem_read(map_at + byte_at, 2), "little") != value:
            changed_calls.append(byte_at//2)

    setter = machine.syms["map_word185"]
    machine.u.hook_add(UC_HOOK_CODE, observe_word, begin=setter, end=setter)
    frames = []
    for g in range(905, 976):
        files = [data / f"frame{g}.{ext}" for ext in ("geometry", "raw")]
        for f in files:
            assert sha(f) == sealed["evidence_files"][f.name]
        geometry, raw = [f.read_bytes() for f in files]
        blocks, _, _ = legacy_packets(geometry, raw, g)
        serial = g - 904
        touched_words.clear()
        changed_calls.clear()
        result = machine.frame(blocks, geometry, raw, g, serial)
        assert result["bank"] == (serial - 1) % 2
        rows = [p.hex() for p in machine.packets if p[1] == 2]
        assert machine.packets[-1][0] == 3 and rows
        layout = machine.layout["nes_native_video165"]
        dirty = int.from_bytes(machine.u.mem_read(machine.video+layout["map_dirty"],8),"little")
        inherits = bool(machine.u.mem_read(machine.video+layout["map_inherit"],1)[0])
        word_mask = sum(1 << word for word in touched_words) if inherits else (1 << 2048)-1
        assert dirty == sum(1 << row for row in range(64) if (word_mask >> (32*row)) & 0xffffffff)
        if inherits:
            assert set(changed_calls) == touched_words
        frames.append(dict(inherits=inherits, changed_calls=list(changed_calls), touched_words_hex=hex(word_mask), generation=g, serial=serial, bank=result["bank"], map_packets=rows,
                           image_sha256=sha(out / f"frame{g}/expected-map.bin"),
                           input_sha256=[sha(f) for f in files]))
        if serial % 10 == 0:
            print(f"Captured {serial} frames", flush=True)
    (out / "captures.json").write_text(json.dumps(frames, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("arm", "data", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    measure(args.arm, args.data, args.out)
