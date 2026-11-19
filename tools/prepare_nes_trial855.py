"""Build a clean MMC826 board with the verified 854E client and name its ARM edition."""
import argparse
import json
import shutil
from pathlib import Path

from nes_raw506 import sha
from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial816 import fit

ROOT = Path(__file__).resolve().parents[1]
CLIENT = PROBES / "nes-column854/client-e"
ARM = PROBES / "nes-column854/link-b/src"
WORK = PROBES / "nes-trial855"


def board(temp):
    base = temp / "nes-trial816-board822held"
    out = temp / "nes-trial816-board855"
    old = json.loads((ROOT / "analysis/trial826-package.json").read_bytes())
    assert sha(base / "output_files/board.sof") == old["image"]["SOF"]
    evidence = json.loads((ROOT / "analysis/column854-results.json").read_bytes())
    assert sha(CLIENT / "sink165.sfc") == evidence["demo"]["1"]["runs"]["on"]["client"]
    rom = (CLIENT / "sink165.sfc").read_bytes()
    assert bytes.fromhex((CLIENT / "sink-program.hex").read_text()) == rom[:5056] + rom[-64:]
    out.mkdir()
    for sub in ("rtl", "sys"):
        shutil.copytree(base / sub, out / sub)
    for p in base.iterdir():
        if p.suffix in (".sv", ".v", ".vhd", ".qpf", ".qsf", ".sdc", ".tcl", ".hex"):
            shutil.copyfile(CLIENT / p.name if p.name == "sink-program.hex" else p, out / p.name)
    assert sha(out / "sink-program.hex") == sha(CLIENT / "sink-program.hex")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("board", "fit", "arm"))
    parser.add_argument("temp", type=Path)
    args = parser.parse_args()
    if args.action == "board":
        board(args.temp)
    elif args.action == "fit":
        fit(args.temp, 855, Path("C:/altera_lite/25.1std/quartus/bin64"))
    else:
        rename_edition(ARM, WORK / "patch", 826, 855)
