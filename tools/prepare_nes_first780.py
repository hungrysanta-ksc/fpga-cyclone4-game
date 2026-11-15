# SPDX-License-Identifier: MIT
"""Offer a completed compact OBJ run at the first forward slot gap on a warm bank."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out):
    path = base / "nes_plan_service200.c"
    assert sha(path) == "6d03c10aed038ba86b229f95701cf92d395356594878ccb33e50ea7b9a4975f2"
    source = once(path.read_text(), " if(!append(p,q))return false;", """ /* The final eight bytes belong to a sorted compact OBJ suffix.
  * A forward slot gap cannot extend its staging DMA. Offer the ready
  * prefix through the normal E9 credit, receipt and cancellation path. */
 if(q->kind==1 && p->bank_history==2 && p->bytes>p->obj_start &&
    q->slot>p->buffer[4+p->bytes-8+3]+1u){
  if(!flush(p))return false;
 }
 if(!append(p,q))return false;""")
    out.mkdir(parents=True, exist_ok=False)
    (out / path.name).write_text(source, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    prepare(args.base, args.out)
