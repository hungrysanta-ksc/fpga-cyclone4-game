"""Recover the retained ROM request on the output-fault exit of the linked ARM."""
import argparse
from pathlib import Path

from nes_raw506 import once


def prepare(src, patch):
    path = src / "nes_run136.inc"
    text = once(path.read_text(), "if(nes_run136.rom_error)(void)ppu154(io);",
                """if(nes_run136.rom_error){
  if(!nes_run136.context_valid)(void)context146(io);
  (void)ppu154(io);
 }""")
    patch.mkdir(parents=True, exist_ok=True)
    (patch / path.name).write_text(text, newline="\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src", type=Path)
    p.add_argument("patch", type=Path)
    a = p.parse_args()
    prepare(a.src, a.patch)
