"""Trace real ARM E8 responses and schedule the next checked OBJ before palette traffic."""
import argparse
import json
from pathlib import Path

from nes_page963 import simulate
from nes_plan_palette972 import BASE, prepare
from nes_raw506 import once


def source(mode):
    if mode == "control":
        return BASE
    if mode == "prefix":
        return BASE.with_name("nes-plan-palette972-prefix")
    return BASE.with_name("nes-token973-"+mode)


def trace(parent):
    class Reader(parent):
        def snapshot557(self, tx, start):
            reply = super().snapshot557(tx, start)
            if self.generation == 911 and tx[0] == 0xe8:
                with (self.a.out/"e8-973.jsonl").open("a") as log:
                    print(json.dumps([start,bytes(reply).hex()]),file=log)
            return reply
    return Reader


def build_source(mode):
    work=source(mode)
    if mode not in ("before96","before232"):
        raise ValueError("Only candidate source is generated")
    prepare(work,True)
    path=work/"link/src/nes_native_sink165.c"
    body=path.read_text()
    slot="!packet(s,2,3,"+("32,p->cgram+32,96)" if mode=="before96" else "128,p->cgram+128,232)")
    # Let the original service path retire this specific outstanding short OBJ
    # and read the next descriptor. The tile remains owned until checked receipt.
    guard="""(s->plan->bulk_pending && s->plan->bulk[1]==1 &&
      s->plan->bulk[2]==32 && !s->plan->bulk[3] &&
      !nes_plan200_progress(s->plan,NES_ORDINARY553)) || """
    path.write_text(once(body,slot,guard+slot),newline="\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("prepare","run"))
    parser.add_argument("mode",choices=("control","prefix","before96","before232"))
    parser.add_argument("temp",type=Path)
    parser.add_argument("--phase",type=int,choices=(1,2),default=1)
    args=parser.parse_args()
    if args.action=="prepare":
        build_source(args.mode)
    else:
        simulate(args.temp,args.phase,"cold",True,source(args.mode),True,feedback=trace,
                 tag="973"+args.mode,edition=966)
