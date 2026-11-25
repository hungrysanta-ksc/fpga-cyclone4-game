"""Replay selected original Kirby source pictures. Private cartridge and images stay local."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from capture_nes_mask820 import capture
from cross_nes1022 import GAMES, rom_path
from replay_nes_mask820 import simulate

ROOT=Path(__file__).resolve().parents[1]
FRAMES=(750,1830,3030,3570)
MESEN=Path("C:/Users/mohallo/AppData/Local/Temp/nes-bonus698-mesen/Mesen.exe")


def geometry(raw,board,out):
    out.mkdir(parents=True,exist_ok=True)
    for f in FRAMES:
        stim=out/str(f)
        subprocess.run([sys.executable,ROOT/"tools/prepare_nes_geometry230.py","--capture",raw,"--prior",raw,
                        "--out",stim,"--first",str(f),"--last",str(f),"--kirby14"],check=True)
        for ext in ("hex","palette"):
            shutil.copy2(stim/f"frame{f}.{ext}",out/f"frame{f}.{ext}")
    def adapt(s):
        return (s.replace("[106:0]","[107:0]").replace("{5'h10,drive[16:0]}","{4'h8,drive[107],drive[16:0]}")
                .replace("nes_native_frame201 frame(.*);","nes_native_frame201 #(.TILE_QUERY(0)) frame(.query_index({1'b0,query_index}),.*);"))
    simulate(board,out,[(f,f) for f in FRAMES],adapt=adapt)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("capture","geometry"))
    p.add_argument("raw",type=Path)
    p.add_argument("--board",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--rom-dir",type=Path,default=Path.home()/"Downloads/test")
    a=p.parse_args()
    if a.action=="capture":
        capture(rom_path(a.rom_dir,"kirby"),MESEN,a.raw.resolve(),FRAMES,expected_sha=GAMES["kirby"])
    else:
        geometry(a.raw.resolve(),a.board.resolve(),a.out.resolve())
