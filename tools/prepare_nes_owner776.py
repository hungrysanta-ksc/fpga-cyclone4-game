# SPDX-License-Identifier: MIT
"""Move the existing optional map wait into the first checked suffix poll.

Experiment on the linked 767 path which actually performs the 496-byte DMA.
"""
import argparse
from pathlib import Path
from nes_raw506 import once


def after_receipt(src, out):
    out.mkdir(exist_ok=False, parents=True)
    p=src/'nes_plan_service200.c'
    source=once(p.read_text(), '   if(!complete485(p))return false;\n  }else if(mode!=NES_FINAL553){',
        """   if(!complete485(p))return false;
   /* A checked OBJ return behind OAM can expose the other immutable bank.
    * The next poll checks STOP and snapshots E8, within the same poll limit. */
   if(p->bulk[1] && p->window && p->window->last[0]==9)continue;
  }else if(mode!=NES_FINAL553){""")
    (out/p.name).write_text(source, encoding='utf8', newline='\n')


def prepare(src, out):
    out.mkdir(exist_ok=False, parents=True)
    sink = (src/'nes_native_sink165.c').read_text()
    begin = sink.index(' /*719 The ACK')
    end = sink.index('  /* Canonical raw CHR', begin)
    wait = sink[begin:end]
    # Arm the existing wait after map emission. Only defer it across the
    # independent ordinary preparation, never across an ordinary enqueue.
    sink = sink[:begin] + ' s->plan_wait776 = true;\n' + sink[end:]
    sink = once(sink, 'static bool packet_wire(', 'bool nes_map_wait776(struct nes_native_sink165 *s){\n'
                ' if(!s->plan_wait776)return true;\n s->plan_wait776=false;\n'
                + wait + ' return true;\n}\nstatic bool packet_wire(')
    sink = once(sink, ' if(op==24)op=2;', ' if(!nes_map_wait776(s))return false;\n if(op==24)op=2;')
    header = (src/'nes_native_sink165.h').read_text()
    header = once(header, 'struct nes_native_sink165 {', 'struct nes_native_sink165 {\n bool plan_wait776;')
    endhdr = header.rindex('#endif')
    header = header[:endhdr] + 'bool nes_map_wait776(struct nes_native_sink165 *s);\n' + header[endhdr:]
    plan = (src/'nes_plan_service200.c').read_text()
    # E8 is a snapshot. Only hold an unseen immutable head across the wait.
    # A repeated or empty snapshot stays subject to the normal retry path.
    plan = once(plan, '   if(!complete485(p))return false;\n   /* A new ready',
                '   if(!nes_map_wait776(p->sink))return fail(p,5);\n'
                '   if(!complete485(p))return false;\n   /* A new ready')
    for name, body in (('nes_native_sink165.c',sink),('nes_native_sink165.h',header),('nes_plan_service200.c',plan)):
        (out/name).write_text(body, encoding='utf8', newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--after-receipt',action='store_true')
    a=p.parse_args()
    (after_receipt if a.after_receipt else prepare)(a.src,a.out)
