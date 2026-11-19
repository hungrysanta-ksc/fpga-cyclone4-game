"""Translate adjacent observed frames and run the collector, with explicit gaps for disabled rendering."""
import argparse
import itertools
import json
from pathlib import Path
import sys
from unittest.mock import patch

from corpus_nes_848 import ids
from prepare_nes_geometry230 import main as geometry
from replay_nes_mask820 import simulate


def prepare(split, out):
    out.mkdir(parents=True, exist_ok=False)
    missing = []
    translated = []
    for f in ids():
        capture = split / str(f)
        if not (capture / "rows.bin").stat().st_size:
            assert not (capture / "ppu-fetch.bin").stat().st_size
            missing.append(f)
            continue
        stim = out / str(f)
        argv = ["geometry230", "--capture", str(capture), "--prior", str(capture), "--out", str(stim),
                "--first", str(f), "--last", str(f)]
        with patch.object(sys, "argv", argv):
            geometry()
        for ext in ("hex", "palette"):
            p = stim / f"frame{f}.{ext}"
            p.rename(out / p.name)
        translated.append(f)
    (out / "index.json").write_text(json.dumps(dict(translated=translated, no_fetch=missing)))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "rtl"))
    p.add_argument("source", type=Path, help="split capture directory, or fitted board sources for rtl")
    p.add_argument("out", type=Path)
    a = p.parse_args()
    if a.mode == "prepare":
        prepare(a.source.resolve(), a.out.resolve())
    else:
        frames = json.loads((a.out / "index.json").read_text())["translated"]
        ranges = []
        for _, group in itertools.groupby(enumerate(frames), key=lambda pair: pair[1] - pair[0]):
            run = [f for _, f in group]
            for i in range(0, len(run), 12):
                chunk = run[i:i+12]
                ranges.append((chunk[0], chunk[-1]))
        simulate(a.source.resolve(), a.out.resolve(), ranges)
