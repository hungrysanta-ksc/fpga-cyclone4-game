# SPDX-License-Identifier: MIT
"""Exchange the first two full three-row packets of the second map page."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base,out,compact):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='d4ea668a8a30c9dbc4b3858a51379abddb2efc3b36e35024f3c7b8531901693a'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    path=out/'src/nes_native_sink165.c'
    code=once(path.read_text(),'  if(!packet(s,early?24:2,2,first*64', '''  /* The cursor stays in scan order. Exchange addresses and payloads only
   * when both three-row packets are present in the frozen map mask. */
  if((((unsigned)(mask>>32))&63)==63 && (first==32 || first==35))first=67-first;
  if(!packet(s,early?24:2,2,first*64''')
    if compact:
        code=once(code,'''  if(!((mask>>g)&1)){g++;continue;}
  unsigned first=g++,count=1;while(g<64&&count<3&&((mask>>g)&1)){g++;count++;}''','''  unsigned bits=(unsigned)(mask>>g);
  if(!(bits&1)){g++;continue;}
  unsigned first=g,count=(bits&7)==7?3:(bits&3)==3?2:1;
  g+=count;''')
    path.write_bytes(code.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--compact',action='store_true')
    args=p.parse_args()
    prepare(args.base,args.out,args.compact)
