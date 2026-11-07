"""Relabel the exact ARM validated with board661, keeping executable functions identical."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from package_nes_window516 import LABELS


def prepare(base, out):
    assert digest(base / "src/obj-nes-100/firmware.stm") == evidence("reader661-verification.json")["ARM"]
    shutil.copytree(base, out, ignore=shutil.ignore_patterns("obj-*", ".dep-*", "*.log", "*.json", "base-*"))
    for name in LABELS:
        path = out / "src" / name
        data = path.read_bytes()
        assert b"643" in data and b"662" not in data
        path.write_bytes(data.replace(b"643", b"662"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("base", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    prepare(a.base, a.out)
