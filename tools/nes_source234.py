# SPDX-License-Identifier: MIT
"""END-count receiver candidate; preserve231 semantic validation/output."""
from pathlib import Path
import shutil
from nes_delta231 import materialize as base_materialize, once, ROOT, sha

PACKET = r'''
static uint16_t crc234(uint16_t c,const uint8_t *p,unsigned n){
 while(n--){c^=(uint16_t)*p++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));}return c;
}
static unsigned word234(const uint8_t *p){return (unsigned)p[0]|((unsigned)p[1]<<8);}
static uint32_t long234(const uint8_t *p){return (uint32_t)word234(p)|((uint32_t)word234(p+2)<<16);}
void nes_source234_abort(struct nes_source234 *d,struct nes_native165 *s){if(d&&s)(void)source_bad234(d,s);}
bool nes_source234_packet(struct nes_source234 *d,struct nes_native165 *s,const uint8_t *b,unsigned n){
 if(!d||!s)return false;
 if(!b||!n||n>243||d->fault)return source_bad234(d,s);
 if(!d->open){
  if(n!=20||b[0]!='N'||b[1]!='4'||b[2]!=1||b[3]>1||word234(b+18))return source_bad234(d,s);
  if(!nes_source234_begin(d,s,long234(b+4),long234(b+8),long234(b+12),(uint16_t)word234(b+16),b[3]!=0))return false;
  d->crc=crc234(0xffff,b,n);return true;
 }
 if(n<3)return source_bad234(d,s);
 unsigned at=word234(b),len=b[2];
 if(!d->geometry){
  if(at==65535){
   if(n!=10||len||b[3]!=3||word234(b+8)!=crc234(d->crc,b,8))return source_bad234(d,s);
   if(!nes_source234_geometry(d,s,word234(b+4),word234(b+6)))return false;
   d->crc=crc234(d->crc,b,8);return true;
  }
  if(len){
   if(n!=len+3||!nes_source234_write(d,s,d->next,at,b+3,len))return source_bad234(d,s);
  }else if(n==13&&b[3]==1){
   uint64_t mask=0;for(unsigned i=0;i<8;i++)mask|=(uint64_t)b[i+5]<<(8*i);
   if(!nes_source234_raster(d,s,d->next,at,b[4],mask))return false;
  }else if(n==7&&b[3]==2&&(b[4]==1||b[4]==255)){
   if(!nes_source234_shift(d,s,d->next,at,b[4]==1?1:-1,(uint16_t)word234(b+5)))return false;
  }else return source_bad234(d,s);
  d->crc=crc234(d->crc,b,n);return true;
 }
 if(at==65535){
  if(n!=6||len||b[3]!=4||word234(b+4)!=crc234(d->crc,b,4))return source_bad234(d,s);
  return nes_source234_end(d,s);
 }
 if(n!=len+3||!nes_source234_raw(d,s,at,b+3,len))return source_bad234(d,s);
 d->crc=crc234(d->crc,b,n);return true;
}
'''


def receiver():
    p=ROOT/'cores/nes/candidate/nes_delta231_receiver.inc'
    s=p.read_text().replace('231','234').replace('"nes_delta234.h"','"nes_source234.h"')
    s=once(s,'bool full,unsigned spans,unsigned bytes)', 'bool full)')
    s=once(s,'||(!spans&&(full||bytes))||spans>5741||bytes>5741','')
    s=once(s,'d->want_spans=(uint16_t)spans;d->want_bytes=(uint16_t)bytes;', 'd->crc=0xffff;')
    s=s.replace('d->spans>=d->want_spans||d->bytes+n>d->want_bytes','d->spans>=5741||d->bytes+n>5741')
    s=once(s,'bool nes_source234_geometry(struct nes_source234 *d,struct nes_native165 *s)',
           'bool nes_source234_geometry(struct nes_source234 *d,struct nes_native165 *s,unsigned spans,unsigned bytes)')
    s=once(s,'d->spans!=d->want_spans||d->bytes!=d->want_bytes','d->spans!=spans||d->bytes!=bytes')
    s=s.replace('\nbool nes_source234_', '\nstatic bool nes_source234_')
    return s+PACKET


def materialize(out):
    pins=base_materialize(out)
    h=ROOT/'cores/nes/candidate/nes_source234.h'
    shutil.copyfile(h,out/h.name);pins[str(h.relative_to(ROOT.parent))]=sha(h)
    (out/'nes_source234_receiver.inc').write_text(receiver(),encoding='utf-8',newline='\n')
    p=out/'nes_native165.c'
    p.write_text(p.read_text()+'\n#include "nes_source234_receiver.inc"\n',encoding='utf-8',newline='\n')
    return pins
