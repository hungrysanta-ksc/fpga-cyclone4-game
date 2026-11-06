# SPDX-License-Identifier: MIT
"""Build matched receive and first-BG interventions on the two-block 637 firmware."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, mode):
    prior=json.loads(Path('analysis/dma637-verification.json').read_bytes())
    assert sha(base/'src/obj-nes-100/firmware.stm')==prior['two']['phases'][0]['candidate']['image']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    if mode in ('receive','both'):
        f=out/'src/nes_native165.c'
        s=f.read_text()
        # Use the same seeded CCITT routine already linked for outgoing E1.
        start=s.index('/* Same unreflected')
        s=s[:start]+'#include "crc.h"\n'+s[s.index('static uint8_t crc8',start):]
        s=once(s,'crc16(rx+1,n)','crc_xmodem_block(0xffff,rx+1,n)')
        # Both envelopes have already validated state, owner, width, and
        # complete destination extent. Only a fully accepted run advances at.
        s=once(s,'for(unsigned i=0;i<n;i++)if(!logical_record(s,0,gen,start+i,v))return false;', '''for(unsigned i=0;i<n;i++)s->maps[start+i]=(uint16_t)v;
  require_tile(s,(unsigned)v&8191,1);
  s->at[0]+=n;s->records+=n;''')
        s=once(s,'''for(unsigned i=0;i<n;i++)if(!logical_record(s,0,gen,start+i,
      (words>>(15*(n-1-i)))&32767))return false;''','''for(unsigned i=n;i;i--){
   unsigned cell=(unsigned)words&32767;
   s->maps[start+i-1]=(uint16_t)cell;require_tile(s,cell&8191,1);
   words>>=15;
  }
  s->at[0]+=n;s->records+=n;''')
        f.write_text(s,newline='\n')
    if mode in ('first','both'):
        f=out/'src/nes_plan_service200.c'
        s=once(f.read_text(),'if(!p->early&&(!p->bank_history||p->count>=4))',
               'if(!p->early)')
        f.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('mode',choices=('receive','first','both'))
    a=p.parse_args();prepare(a.base,a.out,a.mode)
