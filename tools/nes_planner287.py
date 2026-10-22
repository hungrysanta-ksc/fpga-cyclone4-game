# SPDX-License-Identifier: MIT
"""Checked ordinary-row reuse with exact fallback and unchanged allocation."""
from nes_delta231 import once


def patch(s):
    s=once(s,'struct context286 {', '''extern bool nes_resident287_can(const struct nes_resident211 *,const struct nes_native_video165 *,unsigned,unsigned);
extern bool nes_resident287_touch(struct nes_resident211 *,struct nes_native_video165 *,unsigned,struct nes_plan191 *);
unsigned rows_reused287,rows_full287;
struct context286 {''')
    s=once(s,' ctx286.phase=2;return true;',' rows_reused287=rows_full287=0;ctx286.phase=2;return true;')
    s=once(s,'  bool shaped286=false;', '''  bool reuse287=exceptional==0;
  unsigned start287=column225(s->raster[first[g]]),row287=(s->rows[first[g]]>>3)*33;
  for(unsigned x=0;reuse287&&x<33;x++){
   unsigned cell=s->maps[row287+x],column=(start287+x)&63u;
   unsigned at=((column/32)*1024+g*32+column%32)*2;
   unsigned word=p->map[at]|((unsigned)p->map[at+1]<<8);
   if(cell>>15||(word&0xfc00)!=(((bank[g]*4+(cell>>13))<<10)|0x2000)||
      !nes_resident287_can(resident,p,word&1023,cell&8191))reuse287=false;
  }
  if(reuse287){
   for(unsigned x=0;x<33;x++){
    unsigned column=(start287+x)&63u,at=((column/32)*1024+g*32+column%32)*2;
    unsigned slot=(p->map[at]|((unsigned)p->map[at+1]<<8))&1023;
    q.tag=s->maps[row287+x]&8191;
    if(!nes_resident287_touch(resident,p,slot,&q)){cancel286();return 0;}
   }
   rows_reused287++;return 1;
  }
  rows_full287++;
  bool shaped286=false;''')
    return s
