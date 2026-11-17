"""Replay both MMC820 no-input excerpts at their two pinned start clocks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

from prepare_nes_mask820 import WORK


def replay(variant, temp, budget):
    root = WORK.parent / "nes-output823"
    tools = Path(__file__).resolve().parent
    def run(job):
        group, phase = job
        source = "extra01" if group=="earlyB" else "demo-extra01"
        args = [sys.executable, tools/"replay_nes_output822.py", WORK.parent/"nes-tile821"/source,
                group,"jointmirror",str(phase),temp,"823"+variant,budget,root/("link-"+variant)/"src"]
        with (root/f"{variant}-{group}-{phase}.log").open("wb") as log:
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(run, [(g,p) for g in ("demoB","earlyB") for p in (1,2)]))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant")
    parser.add_argument("temp",type=Path)
    parser.add_argument("budget",type=Path)
    args=parser.parse_args()
    replay(args.variant,args.temp,args.budget)
