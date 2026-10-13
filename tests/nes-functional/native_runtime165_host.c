/* SPDX-License-Identifier: MIT */
#include "nes_native_runtime165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 receiver;
static struct nes_native_video165 video;
static struct nes_native_runtime165 run;
static struct { unsigned n;uint8_t tx[259],rx[259]; } trace[1024];
static unsigned count,at,packets,acks,waits,mode,services,transfers;
static uint32_t tick;
static bool pending,in_transfer;
static uint8_t reply[12];
static uint8_t crc8(const uint8_t *p,unsigned n){uint8_t c=0;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(uint8_t)((c<<1)^((c&128)?7:0));}return c;}
static uint16_t crc16(const uint8_t *p,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*p++<<8;for(unsigned j=0;j<8;j++)c=(uint16_t)((c<<1)^((c&32768)?0x1021:0));}return c;}
static uint32_t ticks(void *ctx){(void)ctx;return tick;}
static bool service(void *ctx){(void)ctx;assert(!in_transfer);services++;return !(mode==5&&packets==4);}
static bool exchange(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(!in_transfer);in_transfer=true;transfers++;tick++;
 memset(rx,0,n);
 if(tx[0]>=0xd0&&tx[0]<=0xd3){
  assert(at<count&&trace[at].n==n&&!memcmp(tx,trace[at].tx,n));
  memcpy(rx,trace[at++].rx,n);
  if(mode==6&&at==2)rx[n-1]^=1; /* bad native CRC */
 }else if(tx[0]==0xe1){
  assert(!pending&&n>=19&&n<=259);
  assert(crc16(tx,n-2)==((unsigned)tx[n-2]<<8|tx[n-1]));
  const uint8_t *p=tx+1;assert(p[2]+((unsigned)p[3]<<8)==packets);
  assert(p[4]==1&&!p[5]&&!p[6]&&!p[7]);
  reply[0]=p[0]==3?1:0;reply[1]=p[0];memcpy(reply+2,p+2,8);
  reply[10]=0x65;reply[11]=0x9a;pending=true;waits=0;packets++;
  assert(receiver.state==NES_NATIVE165_COMMITTED&&!run.frames);
  if(mode==4&&packets==4){in_transfer=false;return false;}
 }else {
  assert(tx[0]==0xe0&&n==16);rx[1]=0xf6;
  if(pending){
   assert(receiver.state==NES_NATIVE165_COMMITTED&&!run.frames);
   if(mode==2)tick=run.started+run.limit; /* expiry while ACK outstanding */
   if(mode==7){rx[2]=1;} /* bounded ACK poll exhaustion */
   else if(waits++<3)rx[2]=1;
   else {rx[2]=2;memcpy(rx+3,reply,12);pending=false;acks++;
    if(mode==3&&reply[1]==3)rx[7]^=1; /* stale SEAL serial, valid CRC */
   }
  }
  rx[15]=crc8(rx+1,14);
 }
 in_transfer=false;return true;
}
static void read_trace(const char *path){
 FILE *f=fopen(path,"r");assert(f);char a[519],b[519];unsigned n;
 while(fscanf(f,"%u %518s %518s",&n,a,b)==3){
  assert(count<1024&&n<=259&&strlen(a)==n*2&&strlen(b)==n*2);trace[count].n=n;
  for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(a+i*2,"%2x",&v)==1);trace[count].tx[i]=(uint8_t)v;
   assert(sscanf(b+i*2,"%2x",&v)==1);trace[count].rx[i]=(uint8_t)v;}
  count++;
 }
 fclose(f);assert(count);
}
int main(int argc,char **argv){
 assert(argc==3);read_trace(argv[1]);uint16_t palette[64];FILE *f=fopen(argv[2],"rb");assert(f&&fread(palette,2,64,f)==64);fclose(f);
 for(mode=0;mode<8;mode++){
  at=packets=acks=waits=services=transfers=0;pending=false;tick=mode==1?UINT32_MAX-20u:0;
  assert(nes_runtime165_begin(&run,&receiver,&video,palette,exchange,ticks,service,NULL,1000000));
  unsigned steps=0;while(!run.frames&&nes_runtime165_step(&run))assert(++steps<2048);
  assert(!in_transfer&&services>transfers);
  if(mode<2){assert(run.frames==1&&run.result==0&&at==count&&packets==acks&&acks>30&&receiver.state==NES_NATIVE165_IDLE);}
  else {
   unsigned expected=mode==2?NES_RUNTIME165_DEADLINE:mode==4?NES_RUNTIME165_IO:mode==5?NES_RUNTIME165_SERVICE:mode==6?NES_RUNTIME165_RECEIVE:NES_RUNTIME165_DISPLAY;
   assert(run.result==expected&&!run.frames&&receiver.state!=NES_NATIVE165_IDLE);
   unsigned old=transfers;assert(!nes_runtime165_step(&run)&&transfers==old); /* no retry */
  }
  printf("PASS runtime mode=%u result=%u native=%u packets=%u acks=%u service=%u transfers=%u\n",mode,run.result,at,packets,acks,services,transfers);
 }
 assert(!nes_runtime165_begin(&run,&receiver,&video,palette,exchange,ticks,service,NULL,0));
 assert(run.result==NES_RUNTIME165_ARGUMENT);
 mode=0;assert(nes_runtime165_begin(&run,&receiver,&video,palette,exchange,ticks,service,NULL,100));
 tick+=100;unsigned old=transfers;assert(!nes_runtime165_step(&run)&&run.result==NES_RUNTIME165_DEADLINE&&transfers==old);
 assert(nes_runtime165_begin(&run,&receiver,&video,palette,exchange,ticks,service,NULL,100));
 run.steps=4194304u;assert(!nes_runtime165_step(&run)&&run.result==NES_RUNTIME165_LIMIT&&transfers==old);
 puts("PASS idle deadline and stalled-tick iteration backstop");
 return 0;
}
