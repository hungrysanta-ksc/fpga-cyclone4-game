# SPDX-License-Identifier: MIT
"""Materialize the long-OBJ-run-first experiment on the measured MMC558 ARM."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(arm, out):
    assert sha(arm / 'obj-nes-100/firmware.stm') == '98fe5eeb2d9bfdd7b4be66bc50994b91a88229113dd8f9d4ba5aa3f7ed33f1d9'
    name = 'nes_plan_service200.c'
    code = (arm / name).read_text()
    start = code.index('   unsigned keep=15-cut;')
    end = code.index('\n  }', start)
    code = code[:start] + '''   /* At count 15 only, obj_start remembers the sparse prefix length. */
   p->obj_start=(uint8_t)(cut*8);
   return true;''' + code[end:]
    code = once(code, 'if(cut && cut<=7){',
                'if(cut && cut<=7 && records[cut*8+3]!=records[(cut-1)*8+3]){')
    code = once(code, ' if(p->count==15||p->bytes+n>240)if(!flush(p))return false;', ''' if(p->count==15){
  uint8_t *records=p->buffer+4;
  unsigned prefix=p->obj_start;
  if(encoded[0]==0x81 && encoded[3]==records[14*8+3]+1){
   /* The prefix and run have disjoint slot ranges.
    * Save the sorted sparse prefix beyond the in-place SPI reply. */
   memcpy(records+128,records,prefix);
   memmove(records,records+prefix,120-prefix);
   memcpy(records+120-prefix,encoded,8);
   p->bytes=128-prefix;p->count=p->bytes/8;
   if(!flush(p))return false;
   memcpy(records,records+128,prefix);
   p->bytes=prefix;p->count=prefix/8;
   return true;
  }
  if(!flush(p))return false;
 }
 if(p->bytes+n>240 && !flush(p))return false;''')
    out.mkdir(parents=True, exist_ok=False)
    (out / name).write_text(code, newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    prepare(args.arm, args.out)
