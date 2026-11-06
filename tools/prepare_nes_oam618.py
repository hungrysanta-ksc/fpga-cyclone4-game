# SPDX-License-Identifier: MIT
"""Schedule compact CHR packing between palette and OAM issue on the linked ARM."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, yield_oam=False):
    assert sha(base/'src/obj-nes-100/firmware.stm')=='57b1e20b5edaa67fa4d1ad6cd5ab508570d4bb4c18336e42544ee5c4a501532f'
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    f=out/'src/nes_native_sink165.c'
    s=f.read_text()
    a=s.index('  /* Canonical raw CHR')
    b=s.index('  const uint8_t *parts',a)
    pack=s[a:b]
    s=s[:a]+s[b:]
    s=once(s,' const uint8_t *data[4]={p->map,p->cgram,p->oam,p->hdma};\n','')
    s=once(s,' for(unsigned k=3;k<6;k++)if(!(k==4?oam227(s,data[k-2]):span(s,k,0,data[k-2],size[k])))return false;',
           ''' if(!span(s,3,0,p->cgram,512))return false;
'''+pack.replace('if(p->patch_count<=2)','if(p->patch_count && p->patch_count<=2)')+'''
 if(!oam227(s,p->oam)||!span(s,5,0,p->hdma,p->hdma_size))return false;''')
    if yield_oam:
        # A contiguous right-page prefix longer than one 1152-byte grant
        # needs a second arbitration. Do not pace scattered dirty rows.
        s='#include "nes_cost471.h"\n'+s
        s=once(s,' if(!oam227(s,p->oam)', ''' if((((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu && s->plan){
  for(unsigned i=0;i<2;i++)
   if(!nes_cost474_pause(s->plan->ctx,s->plan->guard,0,false))return fail(s,5);
 }
 if(!oam227(s,p->oam)''')
    f.write_bytes(s.encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','out'):p.add_argument(n,type=Path)
    p.add_argument('--yield-oam',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.yield_oam)
