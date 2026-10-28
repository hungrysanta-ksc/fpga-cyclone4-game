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
#include <windows.h>
#include "nes_palette165.inc"
static struct nes_native165 receiver;
static struct nes_native_video165 video;
static struct nes_resident211 cache;
static struct nes_native_sink165 sink;
static unsigned ordinal,plan_count;static uint32_t tile_token=0x43100000;
static uint8_t chr[8192];
static bool exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;char tmp[80],path[80];unsigned id=++ordinal;
 snprintf(tmp,sizeof tmp,"req-%04u.tmp",id);snprintf(path,sizeof path,"req-%04u.bin",id);
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(p,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 snprintf(path,sizeof path,"ack-%04u.bin",id);DWORD start=GetTickCount();
 do {f=fopen(path,"rb");if(f){assert(fread(ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);return true;}Sleep(1);}while((DWORD)(GetTickCount()-start)<60000);return false;
}
static bool emit(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;assert(bank==cache.target && q->generation==receiver.generation);
 unsigned kind=q->kind==1,n=kind?32:16;uint8_t raw[32]={0};
 if(q->kind!=2)for(unsigned y=0;y<8;y++)if(q->mask&(1u<<y)){
  unsigned low=q->alt[y]==UINT16_MAX?q->tag:q->alt[y];assert(low<512&&q->tag<512);
  raw[y*2]=chr[low*16+q->row[y*2]];raw[y*2+1]=chr[q->tag*16+8+q->row[y*2+1]];
 }
 char path[80];snprintf(path,sizeof path,"tile-%04u.bin",ordinal+1);FILE *f=fopen(path,"wb");assert(f&&fwrite(raw,1,n,f)==n);fclose(f);
 unsigned at=q->slot*n;uint8_t d[12]={1,(uint8_t)kind,(uint8_t)n,0,(uint8_t)at,(uint8_t)(at>>8),(uint8_t)q->generation,(uint8_t)(q->generation>>8)};
 for(unsigned i=0;i<4;i++){d[8+i]=(uint8_t)(tile_token>>(8*i));}tile_token++;plan_count++;return nes_sink195_bulk(&sink,d);
}
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
 nes_resident211_reset(&cache);nes_sink165_reset(&sink,exchange,NULL);
 assert(nes_resident211_begin(&cache,1,true,receiver.generation,emit,NULL));
 assert(nes_sink212_begin(&sink,&cache));
 if(!nes_native_video211_plan(&receiver,native_palette165,&video,&cache)){printf("planner error=%u\n",video.error);return 2;}
 assert(video.valid && cache.prepared && plan_count);
 save("oam-4.bin",video.oam,sizeof video.oam);save("map.bin",video.map,sizeof video.map);
 if(!nes_sink212_seal(&sink,&video,&cache)){printf("seal error=%u state=%u\n",sink.error,sink.state);return 3;}
 assert(sink.displayed && sink.last_generation==receiver.generation && cache.displayed && !cache.open);
 f=fopen("producer-done.txt","w");assert(f);fprintf(f,"1\n");fclose(f);
 printf("PASS 227 sink display generation=%u records=%u blocks=%u plans=%u packets=%u\n",receiver.generation,receiver.records,blocks,plan_count,ordinal);return 0;
}
