# SPDX-License-Identifier: MIT
"""Protect the first BG ROM submission and only expand compact raw packets under measured queue pressure."""
import argparse
from pathlib import Path
from prepare_nes_frontier536 import prepare
from nes_raw506 import once


def patch(src,out,protect_first,raw_only=False):
    prepare(src,out,compact_raw=True)
    if raw_only:
        # The raw-only control uses the exact MMC533 map/planner sources.
        for name in ('nes_native_runtime165.c','nes_planner211.c'):
            (out/name).write_bytes((src/name).read_bytes())
        return
    runtime=(src/'nes_native_runtime165.c').read_text()
    assert 's->sink.plan=&s->plan;' in runtime and 's->plan.window=&s->transport;' in runtime
    p=out/'nes_native_runtime165.c'
    s=p.read_text()
    marker=' if(!s->sink.map_next)return nes_sink527_early(&s->sink,s->video,s->resident);'
    guard=' if(!s->plan.early || s->plan.count)return true;'
    # Do not let a speculative map delay a real first BG flush or a buffered
    # E9 batch. In the narrow policy only the additional offer is restricted.
    s=once(s,marker,guard+'\n'+marker if protect_first else marker+'\n'+guard)
    p.write_text(s,newline='\n')
    p=out/'nes_native_sink165.c'
    s=once(p.read_text(),'#include "nes_plan_service200.h"','#include "nes_plan_service200.h"\n#include "nes_sink_window184.h"')
    s=once(s,'   if(part==0 && packed<=384){','''   bool room=true;
   if(part==0 && packed<=384 && !nes_window532_room(s->plan->window,&room))return fail(s,5);
   if(!room){''')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    policy=p.add_mutually_exclusive_group()
    policy.add_argument('--protect-first',action='store_true')
    policy.add_argument('--raw-only',action='store_true')
    a=p.parse_args();patch(a.arm,a.out,a.protect_first,a.raw_only)
