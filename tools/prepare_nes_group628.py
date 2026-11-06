# SPDX-License-Identifier: MIT
"""Serialize exact changed four-byte groups against a bounded, ACK-published bank image."""
import argparse
from pathlib import Path

from nes_raw506 import once
from prepare_nes_tail627 import prepare

HISTORY = """
/* Only the right page is cached. Five bytes per run of equal 4-byte groups.
 * If an image does not fit, invalidate that bank and send ordinary rows. */
static void publish628(struct nes_native_sink165 *s,const uint8_t *page){
 unsigned bank=(s->serial-1)&1,used=0;
 uint8_t *out=s->history628[bank];
 s->base628[bank]=0;
 for(unsigned i=0;i<2048;){
  unsigned count=1;
  while(count<255 && i+4*count<2048 && !memcmp(page+i,page+i+4*count,4))count++;
  if(used+5>sizeof s->history628[0])return;
  out[used]=count;memcpy(out+used+1,page+i,4);used+=5;i+=4*count;
 }
 s->base628[bank]=s->serial;
}

static unsigned groups628(const struct nes_native_sink165 *s,uint8_t *out,
 unsigned offset,const uint8_t *data,unsigned size){
 unsigned bank=(s->serial-1)&1;
 uint32_t base=s->base628[bank];
 if(!base || base!=s->serial-2 || offset<2048 || offset+size>4096 ||
    (offset&63) || !size || size>192 || (size&63))return 0;
 const uint8_t *run=s->history628[bank];
 const uint8_t *end=run+sizeof s->history628[0];
 unsigned skip=(offset-2048)/4;
 while(run!=end && run[0] && skip>=run[0]){skip-=run[0];run+=5;}
 if(run==end || !run[0])return 0;
 unsigned left=run[0]-skip,mask_bytes=size/32,used=8+mask_bytes;
 memcpy(out,&base,4);memset(out+8,0,mask_bytes);
 unsigned sum=0,weighted=0;
 for(unsigned i=0;i<size;i+=4){
  if(memcmp(data+i,run+1,4)){
   if(used+4>=size)return 0;
   out[8+i/32]|=(uint8_t)(1u<<((i/4)&7));
   memcpy(out+used,data+i,4);used+=4;
  }
  for(unsigned j=i;j<i+4;j+=2){sum+=data[j]+256u*data[j+1];weighted+=sum;}
  if(!--left && i+4<size){
   run+=5;if(run==end || !run[0])return 0;
   left=run[0];
  }
 }
 put16(out+4,sum);put16(out+6,weighted);return used;
}
"""


def build(base,out):
    prepare(base,out,'control')
    src=out/'src'
    def edit(name,fn):
        path=src/name
        path.write_bytes(fn(path.read_text()).encode())
    edit('nes_native_sink165.h',lambda s:once(s,'uint8_t map_next;', '''uint8_t map_next;
 uint8_t history628[2][880];uint32_t base628[2],epoch628;'''))
    def sink(s):
        s=once(s,'static bool packet_wire',HISTORY+'\nstatic bool packet_wire')
        s=once(s,' put16(b+12,n);if(n)memcpy(b+16,data,n);',''' if(b[0]==2 && section==2){
  unsigned packed=groups628(s,b+16,at,data,n);
  if(packed){b[0]=9;put16(b+14,n);n=packed;data=NULL;}
 }
 put16(b+12,n);if(n && data)memcpy(b+16,data,n);''')
        s=once(s,'b[0]==8||bulk_submit','b[0]==8||b[0]==9||bulk_submit')
        s=once(s,' uint8_t b[12];put16(b,0x4891);',''' if(s->epoch628!=r->epoch){
  s->base628[0]=s->base628[1]=0;s->epoch628=r->epoch;
 }
 uint8_t b[12];put16(b,0x4891);''')
        s=once(s,'s->last_generation=s->generation;', 'publish628(s,p->map+2048);s->last_generation=s->generation;')
        return once(s,'s->error=(uint8_t)e;', 's->base628[0]=s->base628[1]=0;s->error=(uint8_t)e;')
    edit('nes_native_sink165.c',sink)
    edit('nes_sink_window184.c',lambda s:once(s,'p[0]!=8&&p[0]!=7','p[0]!=8&&p[0]!=9&&p[0]!=7'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','out'):p.add_argument(k,type=Path)
    a=p.parse_args()
    build(a.base,a.out)
