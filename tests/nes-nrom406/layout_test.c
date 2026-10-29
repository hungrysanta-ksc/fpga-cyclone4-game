// SPDX-License-Identifier: MIT
#include "nes_nrom406.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
 uint8_t h[16]={'N','E','S',0x1a,1,1,0,0};
 struct nes_nrom406_profile p;
 unsigned files,zero;
 for (unsigned prg=1;prg<=2;prg++) for (unsigned mir=0;mir<2;mir++) {
  h[4]=(uint8_t)prg;h[6]=(uint8_t)mir;
  uint32_t size=16u+prg*16384u+8192u;
  assert(nes_nrom406_header(h,size,&p));
  assert(p.prg_bytes==prg*16384u && p.vertical==(mir!=0));
  files=zero=0;
  for(uint32_t at=0;at<0x60000u;at++) {
   bool from;uint32_t pos;
   assert(nes_nrom406_layout(&p,at,&from,&pos));
   if(from) {
    uint32_t expected=at<p.prg_bytes ? 16u+at : 16u+p.prg_bytes+at-0x40000u;
    assert(pos==expected && pos>=16 && pos<size);files++;
   } else {assert(pos==0);zero++;}
  }
  assert(files==prg*16384u+8192u && files+zero==0x60000u);
  bool from;uint32_t pos;
  assert(!nes_nrom406_layout(&p,0x60000u,&from,&pos));
  assert(!nes_nrom406_header(h,size-1,&p));
  assert(!nes_nrom406_header(h,size+1,&p));
 }
 h[4]=1;h[6]=0;
 const uint32_t size=16u+16384u+8192u;
 for(unsigned bit=1;bit<8;bit++) {h[6]=(uint8_t)(1u<<bit);assert(!nes_nrom406_header(h,size,&p));}
 h[6]=0;
 for(unsigned idx=7;idx<16;idx++) {h[idx]=1;assert(!nes_nrom406_header(h,size,&p));h[idx]=0;}
 h[4]=0;assert(!nes_nrom406_header(h,size,&p));h[4]=3;assert(!nes_nrom406_header(h,size,&p));
 h[4]=1;h[5]=0;assert(!nes_nrom406_header(h,size,&p));h[5]=2;assert(!nes_nrom406_header(h,size,&p));
 h[5]=1;h[0]=0;assert(!nes_nrom406_header(h,size,&p));
 assert(!nes_nrom406_header(NULL,size,&p));
 puts("NROM406 HEADER/LAYOUT PASS profiles=4 physical_bytes=1572864 negative_header_and_size");
 return 0;
}
