/* SPDX-License-Identifier: MIT */
#include "nes_trace166.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 r;
static unsigned put(uint8_t *p,unsigned k,unsigned g,unsigned i,uint64_t v){
 static const unsigned widths[8]={2,1,7,3,7,1,2,8};
 unsigned tag=k*8192+i,w=widths[k];p[0]=(uint8_t)(tag>>8);p[1]=(uint8_t)tag;p[2]=(uint8_t)(g>>8);p[3]=(uint8_t)g;
 for(unsigned j=0;j<w;j++)p[4+j]=(uint8_t)(v>>(8*(w-1-j)));
 return 4+w;
}
int main(void){
 uint8_t p[256];unsigned n=0;uint64_t h=((uint64_t)0x1651<<48)|((uint64_t)1<<42)|((uint64_t)1<<36)|((uint64_t)224<<28);
 assert(sizeof(nes_trace166)==48);nes_native165_reset(&r);memset(&nes_trace166,0,sizeof(nes_trace166));nes_trace166.now=10;
 n+=put(p+n,7,65535,0,h);n+=put(p+n,0,65535,0,0);n+=put(p+n,7,65535,2,1);n+=put(p+n,7,0,0,h);
 assert(nes_native165_packet(&r,65535,p,n));
 assert(nes_trace166.begins==2&&nes_trace166.aborts==1&&nes_trace166.records==4);
 assert(nes_trace166.first_abort_reason==1&&nes_trace166.first_abort_generation==65535&&nes_trace166.first_abort_records==1&&nes_trace166.first_abort_bytes==0);
 assert(nes_trace166.first_begin_tick==10&&nes_trace166.first_abort_tick==10&&r.generation==0);
 nes_trace166.now=20;n=put(p,0,0,0,0);n+=put(p+n,7,0,2,4);assert(nes_native165_packet(&r,0,p,n));
 assert(nes_trace166.aborts==2&&nes_trace166.last_abort_reason==4&&nes_trace166.first_abort_reason==1&&nes_trace166.max_records==1);
 n=put(p,7,1,0,h);assert(!nes_native165_packet(&r,8,p,n));assert(nes_trace166.records==6); /* wrong token */
 nes_native165_reset(&r);memset(&nes_trace166,0,sizeof(nes_trace166));
 n=put(p,7,9,0,h);assert(nes_native165_packet(&r,0,p,n));n=put(p,7,8,2,4);
 assert(!nes_native165_packet(&r,1,p,n)&&nes_trace166.aborts==0); /* wrong generation */
 puts("PASS TRACE166 coalesced ABORT/BEGIN; generation/token wrap; first reason retained; two invalid records excluded;48B");return 0;
}
