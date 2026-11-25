"""Separate the single-row raw prefix from its table tail on the MMC1012 link."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from nes_overlap1018 import BASE, ROOT, once, sha
from replay_nes_tail1013 import run

WORK = BASE.with_name("nes-split1020")


MODES = ("stream", "stream_ack", "gap", "gap_ack", "front")
SOURCES = ("nes_native_video165.h", "nes_native_sink165.c", "nes_planner211.c")


def edit(src, mode):
    """Apply the measured source changes to the pinned MMC1012 translation units."""
    patches = ["stream", "front"] if mode == "front" else ["stream"]
    for name in patches:
        patch = Path(__file__).with_name(f"nes_split1020_{name}.patch")
        subprocess.run(["git", "apply", "--unidiff-zero", "--whitespace=nowarn", "-"],
                       cwd=src, input=patch.read_bytes(), check=True)
    for name in SOURCES:
        source = src / name
        source.write_text(source.read_text(), newline="\n")
    sink = src / "nes_native_sink165.c"
    code = sink.read_text()
    issue = "  if(!map527(s,p,0x7fffff,1))return false;"
    if mode.endswith("_ack"):
        code = once(code, issue, issue + "\n  uint8_t ack[12];if(!nes_window184_drain(s->plan->window,ack))return fail(s,5);")
    if mode.startswith("gap"):
        code = once(code, issue, "  uint8_t ready[12];if(!nes_window184_drain(s->plan->window,ready))return fail(s,5);\n" + issue)
    sink.write_text(code, newline="\n")


def prepare(mode):
    original = BASE / "link"
    expected = json.loads((ROOT / "analysis/trial1012-package.json").read_bytes())
    assert sha(original / "src/obj-nes-100/firmware.stm") == expected["firmware"]
    dest = WORK / mode / "link"
    shutil.copytree(original, dest, ignore=shutil.ignore_patterns("*.log"))
    edit(dest / "src", mode)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=MODES)
    parser.add_argument("--temp",type=Path)
    action=parser.add_mutually_exclusive_group()
    action.add_argument("--guards",action="store_true")
    action.add_argument("--phase",type=int,choices=(1,2))
    a=parser.parse_args()
    if a.phase or a.guards:
        if not a.temp:
            parser.error("replay requires --temp")
        tag="1020-"+a.mode
        link=WORK/a.mode
        if a.guards:
            from guard_nes_tail1013 import guards
            guards(a.temp,a.mode,root=link,trace=a.temp/f"nes-tile821-late-jointmirror-p1-{tag}",tag="nes-guard-"+tag)
        else:
            run(a.temp,a.phase,"control",firmware=link/"link/src",tag=tag)
    else:
        prepare(a.mode)
