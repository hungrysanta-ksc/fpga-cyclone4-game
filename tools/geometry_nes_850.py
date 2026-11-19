"""Restore pre-capture PPU dots before sampling the continuous scene transition."""
import argparse
import json
from pathlib import Path
import shutil

from nes_raw506 import once
from replay_nes_mask820 import simulate
from corpus_nes_848 import CLIPS


def prepare(board, original, out, clip="transition"):
    out.mkdir(parents=True,exist_ok=False)
    if clip == "transition":
        ranges = [(1525,1544),(1557,1571),(1572,1586)]
    else:
        start, stop = CLIPS[clip]-2, CLIPS[clip]+60
        ranges = [(f,min(f+11,stop-1)) for f in range(start,stop,12)]
    frames = [f for first,last in ranges for f in range(first,last+1)]
    index = json.loads((original/"index.json").read_bytes())
    assert set(frames).issubset(index["translated"]) and index["no_fetch"] == list(range(1545,1557))
    for f in frames:
        for ext in ("hex","palette"):
            name=f"frame{f}.{ext}"
            shutil.copyfile(original/name,out/name)
    (out/"index.json").write_text(json.dumps(dict(translated=frames,no_fetch=index["no_fetch"])))
    # Count the clocks before capture_begin so that sampled PPUMASK and the
    # row-8 raster context have a real predecessor at scanline 7 dot 257.
    simulate(board,out,ranges,
             adapt=lambda s:once(s,"for(t=7*341+257;","for(t=0;"))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("board","original","out"):
        p.add_argument(name,type=Path)
    p.add_argument("--clip",choices=tuple(CLIPS),default="transition")
    a=p.parse_args()
    prepare(a.board,a.original,a.out,a.clip)
