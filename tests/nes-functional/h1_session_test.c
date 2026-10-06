/* SPDX-License-Identifier: MIT. Callback unit tests, not MCU/board execution. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_h1_session.h"
struct model {bool reset,run;unsigned releases,starts,stops,queries;int fault;uint16_t epoch;};
static void reset(void *ctx,bool held) {
 struct model *m=ctx;m->reset=held;if(!held){assert(m->run);m->releases++;}
}
static bool configure(void *ctx,const char *name) {
 struct model *m=ctx;assert(m->reset);assert(strcmp(name,"/sd2snes/fpga_nh1.bi3")==0);
 if(m->fault==1)return false;
 m->run=false;m->epoch=m->fault==6?UINT16_MAX:0;return true;
}
static bool spi(void *ctx,const uint8_t *tx,uint8_t *rx,size_t n) {
 struct model *m=ctx;memset(rx,0,n);
 if(n==3) {
  assert(m->reset);assert(tx[1]==0xa5&&tx[2]==0x5a);
  if(tx[0]==0xe8){m->starts++;m->run=true;if(m->fault!=4)m->epoch++;if(m->fault==5)return false;}
  else {assert(tx[0]==0xe9);m->stops++;m->run=false;}
  return true;
 }
 assert(n==2);m->queries++;
 switch(tx[0]) {
 case 0xf0:rx[1]=m->fault==2?0:0xa5;break;
 case 0xf1:rx[1]=m->fault==3?0x33:0x34;break;
 case 0xf2:rx[1]=(uint8_t)(2|(m->run?1:0));break;
 case 0xf3:rx[1]=(uint8_t)m->epoch;break;
 case 0xf4:rx[1]=(uint8_t)(m->epoch>>8);break;
 default:assert(0);
 }
 return true;
}
static void delay(void *ctx,unsigned duration){(void)ctx;assert(duration==200);}
int main(void) {
 for(int f=0;f<=6;f++) {
  struct model m={0};m.fault=f;
  struct nes_h1_io io={&m,reset,configure,spi,delay};uint16_t ep=0;
  enum nes_h1_result result=nes_h1_start(&io,&ep);
  if(f==0){assert(result==NES_H1_OK&&ep==1&&m.releases==1);assert(nes_h1_stop(&io)==NES_H1_OK);assert(m.reset&&!m.run);}
  else {assert(result!=NES_H1_OK&&m.reset&&m.releases==0);if(f==4||f==5)assert(m.stops==1&&!m.run);else assert(m.starts==0);}
 }
 puts("PASS H1 SESSION cases=7");return 0;
}
