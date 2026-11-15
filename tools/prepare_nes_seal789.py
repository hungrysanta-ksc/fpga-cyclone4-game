# SPDX-License-Identifier: MIT
"""Restrict producer borrowing to a first sparse map and an actual bulk return wait."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha

BASE = "99325fb07e9d3d0f1385eee328f34acfcbd73a6da9391744904d8ff1b4766266"
CONTROL = "0b0d9c3907488f2cc94e888e5d7678af77f76fabe4d839f2dfbcea79454ccdeb"
MODES = ("first", "first_wait", "first_bulk", "bulk", "control_cost", "first_wait_cost", "first_bulk_cost", "bulk_cost")


def prepare(base, control, out, mode):
    assert sha(base / "obj-nes-100/sd2snes.elf") == BASE
    assert sha(control / "obj-nes-100/sd2snes.elf") == CONTROL
    out.mkdir(parents=True, exist_ok=False)
    share = mode.endswith("_cost")
    mode = mode.removesuffix("_cost")
    if mode.startswith("first"):
        name = "nes_native_sink165.c"
        source = (base / name).read_text()
        source = once(source, " unsigned cursor=s->map_next&127;",
                      " bool first_offer=false;\n unsigned cursor=s->map_next&127;")
        source = once(source, "cursor=first+4;s->deferred783=",
                      "first_offer=s->bg_next && s->obj_next;\n   cursor=first+4;s->deferred783=")
        source = once(source, """  bool adjacent=pair && count==3;
  if(early==3 && s->deferred783 && s->plan->window->last[0]==7 && s->plan->window->last[1]==1)adjacent=true;""",
                      """  /* Borrow for one completed map only after both kinds of bulk were issued.
   * The ordinary E1 admission, STOP and independent receipts still apply. */
  bool adjacent=first_offer || (pair && count==3);
  first_offer=false;""")
        (out / name).write_text(source, newline="\n")
    if share:
        name = "nes_native_sink165.c"
        path = out / name
        source = (path if path.exists() else base / name).read_text()
        helper = """static unsigned wire_cost789(const uint8_t *b,unsigned n,bool split){
 unsigned cost=0;
 while(n){
  unsigned piece=split?span_piece(b,n):(n<240?n:240);
  cost+=data_cost(b,piece);b+=piece;n-=piece;
 }
 return cost;
}
"""
        source = once(source, "static bool span(", helper + "static bool span(")
        lo = source.index(" unsigned oldcost=0,newcost=0;")
        hi = source.index(" /* Synchronous immutable", lo)
        source = source[:lo] + " unsigned oldcost=wire_cost789(b,n,false),newcost=wire_cost789(b,n,true);\n" + source[hi:]
        lo = source.index(" unsigned old=0,split=0;")
        hi = source.index(" return old<split?", lo)
        source = source[:lo] + " unsigned old=wire_cost789(b,n,false),split=wire_cost789(b,n,true);\n" + source[hi:]
        path.write_text(source, newline="\n")
    name = "nes_native_runtime165.c"
    if mode == "first":
        (out / name).write_bytes((control / name).read_bytes())
    if mode in ("first_bulk", "bulk"):
        source = (base / name).read_text()
        source = once(source, "s->resident->prepared && s->plan.ending));",
                      "s->resident->prepared && s->plan.ending && s->transport.last[0]==7));")
        (out / name).write_text(source, newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("base", "control", "out"):
        parser.add_argument(key, type=Path)
    parser.add_argument("mode", choices=MODES)
    args = parser.parse_args()
    prepare(args.base, args.control, args.out, args.mode)
