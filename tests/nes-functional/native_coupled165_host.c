/* SPDX-License-Identifier: MIT */
#include "nes_native_runtime165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
static struct nes_native165 receiver;
static struct nes_native_video165 video;
static struct nes_native_runtime165 run;
static struct {unsigned n;uint8_t tx[259],rx[259];} trace[1024];
static unsigned count,at,packets,acks,services,transfers,mode;
static bool pending,in_transfer;
static uint32_t epoch;
static uint8_t operation;
static uint8_t crc8(const uint8_t *p,unsigned n){uint8_t c=0;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(uint8_t)((c<<1)^((c&128)?7:0));}return c;}
static uint16_t crc16(const uint8_t *p,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*p++<<8;for(unsigned j=0;j<8;j++)c=(uint16_t)((c<<1)^((c&32768)?0x1021:0));}return c;}
static uint32_t ticks(void *ctx){(void)ctx;return (GetTickCount()-epoch)/10;}
static bool service(void *ctx){(void)ctx;assert(!in_transfer);services++;return true;}
static bool exchange(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(!in_transfer);in_transfer=true;transfers++;memset(rx,0,n);
 if(tx[0]>=0xd0&&tx[0]<=0xd3){
  assert(at<count&&trace[at].n==n&&!memcmp(tx,trace[at].tx,n));memcpy(rx,trace[at++].rx,n);
 }else if(tx[0]==0xe1){
  assert(!pending&&n>=19&&n<=259&&crc16(tx,n-2)==((unsigned)tx[n-2]<<8|tx[n-1]));
  assert(receiver.state==NES_NATIVE165_COMMITTED&&!run.frames);
  char tmp[64],name[64];packets++;operation=tx[1];
  snprintf(tmp,sizeof tmp,"req-%04u.tmp",packets);snprintf(name,sizeof name,"req-%04u.bin",packets);
  FILE *f=fopen(tmp,"wb");assert(f&&fwrite(tx+1,1,n-3,f)==n-3);assert(!fclose(f)&&!rename(tmp,name));pending=true;
 }else{
  assert(tx[0]==0xe0&&n==16);rx[1]=0xf6;
  if(pending){
   assert(receiver.state==NES_NATIVE165_COMMITTED&&!run.frames);
   char name[64];snprintf(name,sizeof name,"ack-%04u.bin",packets);FILE *f=fopen(name,"rb");
   if(f){assert(fread(rx+3,1,12,f)==12&&fgetc(f)==EOF);fclose(f);rx[2]=2;pending=false;acks++;
    /* Real client ACK has arrived, but deadline wins before frame consumption. */
    if(mode==1&&operation==3)epoch=GetTickCount()-60000;
   }else {rx[2]=1;Sleep(1);}
  }
  rx[15]=crc8(rx+1,14);
 }
 in_transfer=false;return true;
}
int main(int argc,char **argv){
 assert(argc==4);mode=!strcmp(argv[3],"deadline");FILE *f=fopen(argv[1],"r");assert(f);
 char x[519],y[519];unsigned n;
 while(fscanf(f,"%u %518s %518s",&n,x,y)==3){
  assert(count<1024&&n<=259&&strlen(x)==n*2&&strlen(y)==n*2);trace[count].n=n;
  for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(x+2*i,"%2x",&v)==1);trace[count].tx[i]=(uint8_t)v;assert(sscanf(y+2*i,"%2x",&v)==1);trace[count].rx[i]=(uint8_t)v;}count++;
 }fclose(f);uint16_t palette[64];f=fopen(argv[2],"rb");assert(f&&fread(palette,2,64,f)==64);fclose(f);
 epoch=GetTickCount();assert(nes_runtime165_begin(&run,&receiver,&video,palette,exchange,ticks,service,NULL,6000));
 while(!run.frames&&nes_runtime165_step(&run)){}
 assert(!in_transfer&&at==count&&packets==acks&&acks>30&&services>transfers);
 if(!mode)assert(run.frames==1&&run.result==0&&receiver.state==NES_NATIVE165_IDLE);
 else {assert(!run.frames&&run.result==NES_RUNTIME165_DEADLINE&&receiver.state==NES_NATIVE165_COMMITTED);unsigned old=transfers;assert(!nes_runtime165_step(&run)&&transfers==old);}
 f=fopen("producer-result.json","w");assert(f);fprintf(f,"{\"passed\":true,\"mode\":%u,\"frames\":%lu,\"result\":%u,\"native_transactions\":%u,\"packets\":%u,\"acks\":%u,\"services\":%u,\"transfers\":%u}",mode,(unsigned long)run.frames,run.result,at,packets,acks,services,transfers);fclose(f);
 f=fopen("producer-done.txt","w");assert(f);fputs("done",f);fclose(f);return 0;
}
