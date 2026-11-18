"""Lend SPI to the following captured input after the current SEAL is issued."""
from pathlib import Path
import argparse

from nes_raw506 import once


def prepare(src, out):
    name = "nes_native_runtime165.c"
    body = (src / name).read_text()
    old = "if(reason==3){if(s->sink.bg_next==1 && s->sink.obj_next>=8)s->prefetch_left+=4;reason=2;}"
    # Only the post-send SEAL callback gets the bigger budget. The existing
    # loop stops at COMPLETE, a non-progressing status, STOP, or the cap.
    body = once(body, old, "if(reason==3){s->prefetch_left=16;reason=2;}")
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_bytes(body.encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    prepare(args.src, args.out)
