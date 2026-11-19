"""Prepare linked ARM fixtures and qualify the fitted board input for each source clip."""
import argparse
import json
from pathlib import Path

from check_nes_input848 import run
from corpus_nes_848 import CLIPS
from prepare_nes_tile821 import prepare
from test_nes_mirror822 import test as check_cache


def groups(index):
    absent = set(index["no_fetch"])
    # A missing capture requires a separate recovery replay before the two sides
    # of the transition can be presented as one timed sequence.
    if absent != set(range(1545, 1557)):
        raise ValueError(f"Unrecognized capture gap: {sorted(absent)}")
    return [("opening", range(CLIPS["opening"]-2, CLIPS["opening"]+60)),
            ("before_split", range(CLIPS["transition"]-2, min(absent))),
            ("after_split", range(max(absent)+1, CLIPS["transition"]+60)),
            ("demo", range(CLIPS["demo"]-2, CLIPS["demo"]+60))]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("fixture", "board"))
    for name in ("temp", "rtl", "split", "rom", "arm", "out"):
        p.add_argument(name, type=Path)
    p.add_argument("clip", choices=("opening", "before_split", "after_split", "demo", "transition"))
    p.add_argument("--missed-blank",type=int,default=0,
                   help="number of render-off source frames that never started capture (from lease RTL)")
    a = p.parse_args()
    selection = dict(groups(json.loads((a.rtl / "index.json").read_text())))
    root = a.out / a.clip
    generations = None
    if a.missed_blank and (a.clip != "transition" or not 0 < a.missed_blank < 12):
        p.error("--missed-blank applies only within the render-off transition")
    if a.clip == "transition":
        # The collector increments its generation even when an owned blank
        # capture is discarded. ARM display serials count valid commits only.
        frames = [*selection["before_split"], *selection["after_split"]]
        selection[a.clip] = frames
        generations = {f:905+f-frames[0]-(a.missed_blank if f>=selection["after_split"][0] else 0)
                       for f in frames}
    if a.mode == "fixture":
        prepare(a.rtl, a.split, a.rom, a.arm, root, [(a.clip, selection[a.clip])],
                capture_generations=generations)
    else:
        folder = root / a.clip
        check_cache(a.temp, root, root, a.rom, held=True,
                    inputs=[(root, a.split, a.rtl)], out=a.out / ("hits-" + a.clip))
        run(a.temp / "nes-trial816-board822held", folder, a.arm, a.out / ("sender-" + a.clip))
