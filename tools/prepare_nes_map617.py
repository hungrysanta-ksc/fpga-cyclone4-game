# SPDX-License-Identifier: MIT
"""Offer successive complete left-page map runs while the ARM plans BG rows."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out):
    src = base / 'src'
    assert sha(src/'obj-nes-100/firmware.stm') == '3bc0e5805c03ca3c79cc3d350db77ba490261f5a09f8a074b4d5c898a85306cc'
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log'))
    planner = out/'src/nes_planner211.c'
    s = once(planner.read_text(), 'bool offered=false;', 'unsigned next_offer=3;')
    s = once(s, 'resident->offer_map && !offered && g>=3', 'resident->offer_map && g>=next_offer')
    s = once(s, 'offered=true;if(!resident->offer_map', '''/* At most three rows per packet. The next trigger must be beyond
    * every row this offer could enqueue, including with sparse masks. */
   next_offer=g+3;if(!resident->offer_map''')
    s = once(s, 'if(!offered && resident->offer_map', 'if(next_offer==3 && resident->offer_map')
    planner.write_bytes(s.encode())
    sink = out/'src/nes_native_sink165.c'
    s = once(sink.read_text(), 'if(s->map_next)return true;', 'if(s->map_next>=64)return true;')
    s = once(s, 's->map_next=128; /* Tried once. Low seven bits count rows preceding the suffix. */', '')
    # Leave a refused first offer to the END/suffix path. On a later refusal
    # the cursor must still point to the first unissued row.
    s = once(s, 'return !ready||map527(', 'if(!ready){if(!s->map_next)s->map_next=128;return true;}\n return map527(')
    sink.write_bytes(s.encode())
    service = out/'src/nes_plan_service200.c'
    s = once(service.read_text(), 'if((uint16_t)(p->window->sent-p->window->retired)>=3)return true;',
             '''if((uint16_t)(p->window->sent-p->window->retired)>=3 ||
    (p->bulk_pending && (uint16_t)(p->window->sent-p->bulk_until)>=3))return true;''')
    service.write_bytes(s.encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    prepare(args.base, args.out)
