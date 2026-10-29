// SPDX-License-Identifier: MIT
// Replay actual CRC-checked RTL blocks through the unmodified 227 receiver.
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "nes_native165.h"
#include "nes_resident211.h"
#include "nes_native_sink165.h"
#include "nes_sink_bulk195.h"
#include "nes_plan_service200.h"
#include <windows.h>
#include "nes_palette165.inc"
static struct nes_native165 receiver;
static struct nes_native_video165 video;
static struct nes_resident211 cache;
static struct nes_native_sink165 sink;
static struct nes_plan200 plan;
static unsigned rpc_seq=1;
static void rpc(unsigned op,unsigned addr,const uint8_t *data,unsigned n,uint8_t *reply,unsigned want){
 char tmp[80],path[80];sprintf(tmp,"H-%06u.tmp",rpc_seq);sprintf(path,"H-%06u.req",rpc_seq);
 uint8_t h[8]={(uint8_t)op,(uint8_t)addr,(uint8_t)(addr>>8),(uint8_t)(addr>>16),(uint8_t)n,(uint8_t)(n>>8),0,0};
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(h,1,8,f)==8);if(data)assert(fwrite(data,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 sprintf(path,"H-%06u.rsp",rpc_seq++);DWORD start=GetTickCount();while(!(f=fopen(path,"rb"))){assert(GetTickCount()-start<120000);Sleep(1);}
 if(want)assert(fread(reply,1,want,f)==want);assert(fgetc(f)==EOF);fclose(f);
}
static bool guard(void *ctx){(void)ctx;return true;}
static bool spi(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){(void)ctx;rpc(1,0,tx,n,rx,n);return true;}
static unsigned ordinal,plan_count;
static uint8_t chr[8192];
static bool exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;char tmp[80],path[80];unsigned id=++ordinal;
 snprintf(tmp,sizeof tmp,"req-%04u.tmp",id);snprintf(path,sizeof path,"req-%04u.bin",id);
 if(p[0]==7){unsigned len=p[14]+256u*p[15];assert(len>0&&len<=2048);uint8_t raw[2048];rpc(2,0x400800,NULL,len,raw,len);char tile[80];sprintf(tile,"tile-%04u.bin",id);FILE *tf=fopen(tile,"wb");assert(tf&&fwrite(raw,1,len,tf)==len);fclose(tf);}
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(p,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 snprintf(path,sizeof path,"ack-%04u.bin",id);DWORD start=GetTickCount();
 do {f=fopen(path,"rb");if(f){assert(fread(ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);return true;}Sleep(1);}while((DWORD)(GetTickCount()-start)<60000);return false;
}
static bool emit(void *ctx,unsigned bank,const struct nes_plan191 *q){(void)ctx;assert(bank==cache.target && q->generation==receiver.generation);plan_count++;return nes_plan200_emit(&plan,q);}
static void save(const char *name,const void *p,size_t n){FILE *f=fopen(name,"wb");assert(f && fwrite(p,1,n,f)==n);fclose(f);}

static unsigned calls;
static uint8_t crc8(uint8_t c,uint8_t v){c^=v;for(int i=0;i<8;i++)c=(c&0x80)?(uint8_t)((c<<1)^7):(uint8_t)(c<<1);return c;}
static bool reply(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(n==8);assert(tx[0]==(calls==1?0xd3:0xd0));if(calls==1)assert(tx[4]==1 && (((unsigned)tx[2]<<8)|tx[3])==receiver.generation);
 memset(rx,0,n);rx[1]=0xd6;rx[2]=2;uint8_t c=0;for(int i=1;i<7;i++)c=crc8(c,rx[i]);rx[7]=c;calls++;return true;
}
int main(int argc,char **argv){
 assert(argc==3);FILE *f=fopen(argv[2],"rb");assert(f&&fseek(f,16400,SEEK_SET)==0&&fread(chr,1,sizeof chr,f)==sizeof chr);fclose(f);f=fopen(argv[1],"r");assert(f);nes_native165_reset(&receiver);
 unsigned token,n,blocks=0,prepared=0;char hex[513];uint8_t bytes[256];
 while(fscanf(f,"%u %u %512s",&token,&n,hex)==3){
  assert(n>0 && n<=256 && strlen(hex)==n*2);for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(hex+2*i,"%2x",&v)==1);bytes[i]=(uint8_t)v;}
  if(receiver.state==NES_NATIVE165_COMPLETE){assert(!prepared);assert(nes_native165_prepare(&receiver,true,reply,NULL));assert(calls==3);prepared=1;}
  assert(nes_native165_packet(&receiver,(uint16_t)token,bytes,n));blocks++;
 }
 assert(feof(f));fclose(f);assert(prepared && receiver.state==NES_NATIVE165_COMMITTED && blocks>=2);
 uint8_t image[162];image[0]=4;image[1]=0;memcpy(image+2,chr,160);rpc(4,0,image,sizeof image,NULL,0);rpc(5,0,NULL,0,NULL,0);
 nes_resident211_reset(&cache);nes_sink165_reset(&sink,exchange,NULL);
 memset(&plan,0,sizeof plan);plan.sink=&sink;plan.transfer=spi;plan.guard=guard;plan.poll_limit=65536;
 assert(nes_resident211_begin(&cache,1,true,receiver.generation,emit,NULL));
 assert(nes_sink212_begin(&sink,&cache));
 if(!nes_native_video211_plan(&receiver,native_palette165,&video,&cache)){printf("planner error=%u\n",video.error);return 2;}
 assert(video.valid && cache.prepared && plan_count);assert(nes_plan200_finish(&plan));
 save("oam-4.bin",video.oam,sizeof video.oam);save("map.bin",video.map,sizeof video.map);
 if(!nes_sink212_seal(&sink,&video,&cache)){printf("seal error=%u state=%u\n",sink.error,sink.state);return 3;}
 assert(sink.displayed && sink.last_generation==receiver.generation && cache.displayed && !cache.open);
 assert(nes_plan200_retire(&plan));rpc(9,0,NULL,0,NULL,0);
 f=fopen("producer-done.txt","w");assert(f);fprintf(f,"1\n");fclose(f);
 printf("PASS NROM434 joined display generation=%u records=%u blocks=%u plans=%u packets=%u\n",receiver.generation,receiver.records,blocks,plan_count,ordinal);return 0;
}
