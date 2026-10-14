/* SPDX-License-Identifier: MIT */
#include "nes_native_video165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 s;
static struct nes_native_video165 p;
/* Host only: external pattern storage, never added to MCU RAM. */
static uint8_t bg[1024][16];
static bool stage(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 (void)ctx;assert(kind==0&&slot<1024&&n==16);memcpy(bg[slot],b,n);return true;
}
static bool packet(unsigned k,unsigned index,uint64_t v,unsigned bytes){
 uint8_t b[12]={(uint8_t)((k<<5)|(index>>8)),(uint8_t)index,0,1};
 for(unsigned i=0;i<bytes;i++)b[4+i]=(uint8_t)(v>>((bytes-1-i)*8));
 return nes_native165_packet(&s,s.next_token,b,4+bytes);
}
static void start(unsigned magic){
 nes_native165_reset(&s);
 bool ok=packet(7,0,((uint64_t)magic<<48)|((uint64_t)1<<42)|((uint64_t)1<<36)|((uint64_t)224<<28)|((uint64_t)1<<12),8);
 assert(ok==(magic==0x1741));
}
static unsigned slot(unsigned g,unsigned x){unsigned a=((x/32)*1024+g*32+x%32)*2;return(p.map[a]|((unsigned)p.map[a+1]<<8))&1023;}
int main(void){
 start(0x1651);assert(s.error==2);start(0x1741);
 /* Isolate exception decoding after earlier geometry records. */
 s.at[0]=s.counts[0];s.at[1]=s.counts[1];s.next_kind=3;
 uint32_t e=(200u<<19)|((185u*33+30)<<6)|(7u<<3);
 assert(packet(3,0,e,4));assert(s.exceptions[0]==e&&s.missing==1&&(s.required[50]&3)==1);
 start(0x1741);s.at[0]=s.counts[0];s.at[1]=s.counts[1];s.next_kind=3;
 assert(!packet(3,0,(200u<<19)|(7392u<<6),4)&&s.error==11);
 start(0x1741);s.at[0]=s.counts[0];s.at[1]=s.counts[1];s.next_kind=3;
 assert(!packet(3,0,e,3)&&s.error==20);
 memset(&s,0,sizeof(s));s.state=NES_NATIVE165_COMMITTED;s.generation=1;
 s.counts[0]=33;s.counts[1]=224;s.counts[3]=1;s.counts[4]=224;s.counts[5]=32;
 for(unsigned x=0;x<33;x++)s.maps[x]=100;
 for(unsigned y=0;y<224;y++){s.rows[y]=y&7;s.raster[y]=(uint64_t)0x1e<<36;}
 s.exceptions[0]=e;s.ntiles=2;s.tiles[0].tag=100;s.tiles[1].tag=200;
 for(unsigned i=0;i<2;i++){s.tiles[i].kind=1;for(unsigned j=0;j<16;j++)s.tiles[i].data[j]=(uint8_t)(j+i*64);}
 uint16_t lut[64]={0};assert(nes_native_video165_build(&s,lut,&p,stage,NULL));
 unsigned at=slot(23,30);assert(bg[at][2]==64&&bg[at][3]==15);
 assert(slot(23,29)!=at);assert(bg[slot(23,29)][2]==1&&bg[slot(23,29)][3]==9);
 s.tiles[1].kind=0;assert(!nes_native_video165_build(&s,lut,&p,stage,NULL)&&p.error==6);s.tiles[1].kind=1;
 s.counts[3]=2;s.exceptions[1]=(201u<<19)|(e&0x7ffff);assert(!nes_native_video165_build(&s,lut,&p,stage,NULL)&&p.error==4);
 s.counts[3]=1;s.exceptions[0]=(200u<<19)|(7392u<<6);assert(!nes_native_video165_build(&s,lut,&p,stage,NULL)&&p.error==4);
 printf("PASS CROSS174 C old-ABI/coordinate/width/missing-low/duplicate-cell; exact two-source bytes; context=%u plan=%u\n",(unsigned)sizeof(s),(unsigned)sizeof(p));
 return 0;
}
