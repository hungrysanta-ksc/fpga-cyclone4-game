# SPDX-License-Identifier: MIT
"""Batch tentative patterns using disjoint lifetimes in the existing candidate.

BG: first240 OAM bytes until BG flush; then clear all OAM before OBJ build.
OBJ: first224 CGRAM bytes until OBJ flush; then clear CGRAM before palette build.
No new context, retry, display commit, wire opcode, or FPGA/SNES change.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha

def replace(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)

def converter(s):
 s=replace(s,' const uint8_t zero[16]={0};if(!stage(ctx,0,0,zero,16))return fail(p,14);',
 ''' /* Slot0 is already zero in OAM scratch. Flush15 contiguous BG tiles
  * per packet. OAM has no sprite contents until this phase completes. */''')
 s=replace(s,'  if(slot==previous&&!stage(ctx,0,slot,b,16))return fail(p,14);',
 '''  if(slot==previous){
   memcpy(p->oam+(slot%15)*16,b,16);
   if(slot%15==14&&!stage(ctx,0,slot-14,p->oam,240))return fail(p,14);
  }''')
 s=replace(s,' for(unsigned i=0;i<128;i++)p->oam[i*4+1]=240;',
 ''' if(p->bg_count%15&&!stage(ctx,0,p->bg_count-p->bg_count%15,p->oam,(p->bg_count%15)*16))return fail(p,14);
 /* No callback retains scratch pointers; only ACKed tentative bytes persist.
  * Clear all544 bytes, including high-OAM, before changing its lifetime. */
 memset(p->oam,0,sizeof(p->oam));
 for(unsigned i=0;i<128;i++)p->oam[i*4+1]=240;''')
 s=replace(s,'   if(slot==previous&&!stage(ctx,1,slot,b,32))return fail(p,14);',
 '''   if(slot==previous){
    memcpy(p->cgram+(slot%7)*32,b,32);
    if(slot%7==6&&!stage(ctx,1,slot-6,p->cgram,224))return fail(p,14);
   }''')
 s=replace(s,' put16(p->cgram,lut[s->palette[0]]);',
 ''' if(p->obj_count%7&&!stage(ctx,1,p->obj_count-p->obj_count%7,p->cgram,(p->obj_count%7)*32))return fail(p,14);
 /* CGRAM becomes the palette only after the final OBJ ACK. */
 memset(p->cgram,0,sizeof(p->cgram));
 put16(p->cgram,lut[s->palette[0]]);''')
 return s

def sink(s):
 s=replace(s,' if(!b||kind>1||slot>=(kind?128u:1024u)||n!=(kind?32u:16u)||slot!=(kind?s->obj_next:s->bg_next))return fail(s,4);',
 ''' if(!b||kind>1||!n||n>240||n%(kind?32u:16u)||slot>=(kind?128u:1024u)||
    n/(kind?32u:16u)>(kind?128u:1024u)-slot||slot!=(kind?s->obj_next:s->bg_next))return fail(s,4);''')
 s=replace(s,' if(!packet(s,2,kind,slot*n,b,n))return false;',
 ' if(!packet(s,2,kind,slot*(kind?32u:16u),b,n))return false;')
 s=replace(s,' if(kind)s->obj_next++;else s->bg_next++;',
 ' if(kind)s->obj_next+=(uint16_t)(n/32);else s->bg_next+=(uint16_t)(n/16);')
 return s

def header(s):
 return replace(s,'/* kind0=BG16 bytes, kind1=OBJ32 bytes, slot is SNES pattern index.',
 '''/* kind0=BG multiples of16 bytes, kind1=OBJ multiples of32 bytes, <=240.
 * slot is the first contiguous SNES pattern index. The callback must consume
 * bytes synchronously before returning; the pointer expires at return.''')

def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='bb2e47f0eb5100ee173b94fb9e4a9bfd296e8c5ea9b9946e0b38adac65506bc1'
 m=json.loads((prior/'preparation-cross174.json').read_bytes())
 pins=m['copied']|m['changed']|m['added'];out.mkdir(parents=True,exist_ok=False)
 r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p);r['copied'][n]=h
 for n,fn in [('src/nes_native_video165.c',converter),('src/nes_native_sink165.c',sink),('src/nes_native_video165.h',header)]:
  (out/n).write_text(fn((out/n).read_text()),encoding='utf-8',newline='\n');r['changed'][n]=sha(out/n)
 r['batch_contract']=__doc__;r['prior_firmware_sha256']=sha(prior/'src/obj-nes-100/firmware.stm')
 r['generator_sha256']=sha(Path(__file__))
 for n in ['preparation-batch174.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.prior,a.out)
