/* SPDX-License-Identifier: MIT */
#include "nes_trace166.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 r;
static void meta(uint8_t *p,unsigned gen,unsigned index,uint64_t v){
 p[0]=0xe0;p[1]=(uint8_t)index;p[2]=(uint8_t)(gen>>8);p[3]=(uint8_t)gen;
 for(unsigned i=0;i<8;i++)p[4+i]=(uint8_t)(v>>(56-8*i));
}
int main(void){
 uint8_t p[24];uint64_t h=((uint64_t)0x1651<<48)|((uint64_t)1<<42)|((uint64_t)1<<36)|((uint64_t)224<<28);
 for(unsigned detail=0;detail<16;detail++){
  nes_native165_reset(&r);memset(&nes_trace166,0,sizeof(nes_trace166));
  meta(p,12,0,h);meta(p+12,12,2,(detail<<4)|4);
  assert(nes_native165_packet(&r,0,p,24));
  assert(nes_trace166.begins==1&&nes_trace166.aborts==1&&nes_trace166.ends==0&&nes_trace166.commits==0);
  assert(nes_trace166.first_abort_reason==((detail<<4)|4));
  assert((nes_trace166.first_abort_reason>>4)==detail&&(nes_trace166.first_abort_reason&15)==4);
  meta(p,13,0,h);meta(p+12,13,2,1);assert(nes_native165_packet(&r,1,p,24));
  assert(nes_trace166.first_abort_reason==((detail<<4)|4)&&nes_trace166.last_abort_reason==1);
 }
 assert(sizeof(nes_trace166)==48);puts("PASS ABORT167 16 fill nibbles; first detail retained across next generation;48B");return 0;
}
