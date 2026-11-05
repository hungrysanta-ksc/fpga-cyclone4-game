# SPDX-License-Identifier: MIT
"""Compare equivalent linear span lookahead and one contiguous HDMA-table span."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, policy, close_bg=False):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='792d8407716b97fe708319552c5bb079026a7e1b643b84868bf5349d374135da'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    path=out/'src/nes_native_sink165.c'
    code=path.read_text()
    if policy in ('linear','both'):
        code=once(code,' for(unsigned i=1;i<end&&i+64<=n;i++)if(repeat_bytes(b+i,64)==64)return i;',
                  ''' /* The first 62 consecutive matches two bytes apart start a 64B run.
  * Search starts 1..end-1. A run at zero was handled above. */
 unsigned matches=0;
 for(unsigned j=3;j<n && j<end+63;j++){
  if(b[j]!=b[j-2])matches=0;
  else if(++matches==62)return j-63;
 }''')
    if policy in ('tables','both'):
        start=code.index('  const uint8_t *parts[4]')
        end=code.index('  uint8_t tail[6]',start)
        code=code[:start]+'''  /* Read the enclosing object representation, including all table padding
   * bytes on the wire, but never C alignment padding before size[]. */
  _Static_assert(__builtin_offsetof(struct nes_native_video165,patch.enable)==
                 __builtin_offsetof(struct nes_native_video165,patch.mode)+162,"HDMA table layout");
  if(!span(s,5,offset,raw,packed))return false;
  offset+=packed;
  const uint8_t *tables=(const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.mode);
  if(!span(s,5,offset,tables,243))return false;
  offset+=243;
'''+code[end:]
    path.write_bytes(code.encode())
    if close_bg:
        path=out/'src/nes_plan_service200.c'
        code=path.read_text()
        code=once(code,'  if(p->bank_history==2&&p->sent==1&&p->count==7)return flush(p);\n }',
                  ''' }
 /* Flush on the original BG boundary or the first eight-byte compact OBJ
  * after six records. Extended forms can vary in length, so inspect the
  * actual sorted suffix, not an assumed byte length of its prefix. */
 if(p->bank_history==2 && p->sent==1 && p->count==7 &&
    (q->kind==0 || (q->kind==1 && p->bytes-p->obj_start==8)))return flush(p);''')
        path.write_bytes(code.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','out'):
        p.add_argument(key,type=Path)
    p.add_argument('policy',choices=('original','linear','tables','both'))
    p.add_argument('--close-bg',action='store_true')
    a=p.parse_args()
    if a.policy=='original' and not a.close_bg:
        p.error('original requires --close-bg; use the pinned baseline for an unchanged build')
    prepare(a.base,a.out,a.policy,a.close_bg)
