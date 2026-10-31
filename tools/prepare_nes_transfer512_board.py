# SPDX-License-Identifier: MIT
"""Materialize one whole-board comparison from the verified 507 input list."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import sha

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("board", "candidate", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    p.add_argument("--variant", choices=["input", "map", "both"], required=True)
    a = p.parse_args()
    pins = json.loads((a.board / "source-pins.json").read_text())["board_inputs"]
    a.out.mkdir(parents=True, exist_ok=False)
    for name, expected in pins.items():
        assert sha(a.board / name) == expected, name
        dest = a.out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.board / name, dest)
    for name in ("board.qpf", "nominal204.sdc"):
        shutil.copyfile(a.board / name, a.out / name)
    if a.variant != "map":
        shutil.copyfile(a.candidate / "nes_native_spi165.sv", a.out / "nes_native_spi165.sv")
    if a.variant != "input":
        shutil.copyfile(a.candidate / "client/sink-program.hex", a.out / "sink-program.hex")
    print([name for name in pins if sha(a.out / name) != pins[name]])
