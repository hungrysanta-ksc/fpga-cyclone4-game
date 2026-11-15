"""Build a fresh Quartus project from the MMC763/798 board sources."""
import argparse
import shutil
from pathlib import Path

from probe_nes_fortress800 import compact_reader, preview_ppu


def prepare(base, dest, compact):
    if dest.exists() or base.resolve() in dest.resolve().parents:
        raise ValueError("choose a fresh directory outside the source project")
    dest.mkdir(parents=True)
    for item in base.iterdir():
        if item.name in ("rtl", "sys"):
            shutil.copytree(item, dest / item.name)
        elif item.is_file() and item.suffix not in (".log", ".rpt", ".summary"):
            shutil.copy2(item, dest / item.name)
    ppu = dest / "rtl/ppu.sv"
    ppu.write_text(preview_ppu(ppu.read_text()), newline="\n")
    if compact:
        reader = dest / "nes_rom_service.sv"
        reader.write_text(compact_reader(reader.read_text()), newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    prepare(args.base, args.dest, args.compact)
