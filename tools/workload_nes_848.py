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
    p.add_argument("clip", choices=("opening", "before_split", "after_split", "demo"))
    a = p.parse_args()
    selection = dict(groups(json.loads((a.rtl / "index.json").read_text())))
    root = a.out / a.clip
    if a.mode == "fixture":
        prepare(a.rtl, a.split, a.rom, a.arm, root, [(a.clip, selection[a.clip])])
    else:
        folder = root / a.clip
        check_cache(a.temp, root, root, a.rom, held=True,
                    inputs=[(root, a.split, a.rtl)], out=a.out / ("hits-" + a.clip))
        run(a.temp / "nes-trial816-board822held", folder, a.arm, a.out / ("sender-" + a.clip))
