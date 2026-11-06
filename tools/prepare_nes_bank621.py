# SPDX-License-Identifier: MIT
"""Select the second BG flush from bank history already committed by the consumer."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out):
    assert sha(base/'src/obj-nes-100/firmware.stm') == '3ef55cb4344db1bb924e85937f9d749810b5b24115e596ede61e01fc5fca9e5e'
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log'))
    src = out/'src'
    path = src/'nes_plan_service200.h'
    header = once(path.read_text(), 'bool defer_first,early,ending;', '''uint8_t bank_history; /* 0 = first display, 1 = first fill, 2 = reused target */
 bool early,ending;''')
    path.write_bytes(header.encode())
    path = src/'nes_native_runtime165.c'
    runtime = once(path.read_text(), ' s->plan.defer_first=s->resident->displayed;\n', '')
    runtime = once(runtime, '  if(!planner221(s))', '''  /* Slot zero is fixed. BEGIN has applied epoch invalidation; only a checked
   * visible commit can have set this target bank's resident bit. Sample it
   * before the planner marks the mandatory zero tile dirty again. */
  s->plan.bank_history=s->resident->displayed ?
      1+(s->resident->resident[s->resident->target][0]&1) : 0;
  if(!planner221(s))''')
    path.write_bytes(runtime.encode())
    path = src/'nes_plan_service200.c'
    service = once(path.read_text(), '!p->defer_first', '!p->bank_history')
    service = once(service, 'if(p->defer_first&&p->sent==1', 'if(p->bank_history==2&&p->sent==1')
    path.write_bytes(service.encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for k in ('base', 'out'):
        parser.add_argument(k, type=Path)
    args = parser.parse_args()
    prepare(args.base, args.out)
