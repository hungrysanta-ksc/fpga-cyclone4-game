/* SPDX-License-Identifier: MIT */
/* Actual planner + real transport; the peer65816 owns WRAM/VRAM/ACK. */
#include "nes_native_sink165.h"
#include "nes_sink_bulk195.h"
#include <windows.h>
static struct nes_native_sink165 sink;
static unsigned ordinal,requests,wire_bytes,tile_bytes;
static uint32_t token=0x21200000;
static bool reference;
static const char *mode;
static bool exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;char tmp[80],path[80];unsigned id=++ordinal;
 snprintf(tmp,sizeof tmp,"req-%04u.tmp",id);snprintf(path,sizeof path,"req-%04u.bin",id);
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(p,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 requests++;wire_bytes+=n;snprintf(path,sizeof path,"ack-%04u.bin",id);
 DWORD start=GetTickCount();
 do {f=fopen(path,"rb");if(f){assert(fread(ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);
   if(!strcmp(mode,"wrong_display_ack")&&p[0]==3&&p[8]==2){assert(ack[0]==1);ack[8]^=1;}
   return true;}Sleep(1);}while((DWORD)(GetTickCount()-start)<60000);
 return false;
}
static bool real_stage(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 (void)ctx;return nes_sink165_pattern(&sink,kind,slot,b,n);
}
static bool write_slot(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;assert(bank==cache.target&&(!cache.displayed||bank!=cache.active));
 unsigned kind=q->kind==1,n=kind?32:16;uint8_t raw[32]={0};
 if(q->kind!=2)for(unsigned y=0;y<8;y++)if(q->mask&(1u<<y)){
  raw[y*2]=bytes(q->alt[y]==UINT16_MAX?q->tag:q->alt[y])[q->row[y*2]];
  raw[y*2+1]=bytes(q->tag)[8+q->row[y*2+1]];
 }
 char path[80];snprintf(path,sizeof path,"tile-%04u.bin",ordinal+1);
 FILE *f=fopen(path,"wb");assert(f&&fwrite(raw,1,n,f)==n);fclose(f);tile_bytes+=n;
 unsigned at=q->slot*n;uint8_t d[12]={1,(uint8_t)kind,(uint8_t)n,0,(uint8_t)at,(uint8_t)(at>>8),(uint8_t)q->generation,(uint8_t)(q->generation>>8)};
 for(unsigned i=0;i<4;i++)d[8+i]=(uint8_t)(token>>(8*i));
 token++;
 return nes_sink195_bulk(&sink,d);
}
static bool frame(unsigned variant,unsigned gen){
 source(variant,gen);convert_input();
 if(reference){
  if(!nes_sink165_begin(&sink,(uint16_t)gen))return false;
  if(!reference203_build(&r,lut,&ref,false,real_stage,NULL))return false;
  return nes_sink165_seal(&sink,&ref,5000);
 }
 if(!nes_resident211_begin(&cache,1,true,(uint16_t)gen,write_slot,NULL)||!nes_sink212_begin(&sink,&cache))return false;
 if(!nes_native_video211_plan(&input,lut,&candidate,&cache))return false;
 if(gen==2&&!strcmp(mode,"missing_map"))cache.map_upload&=~(UINT64_C(1)<<63);
 if(gen==1&&!strcmp(mode,"pressure")){
  /* Deliberately unused slots exercise the same checked bulk path and the
   * multi-command VBlank budget without changing a reference pixel. */
  uint8_t raw[2048];for(unsigned i=0;i<sizeof raw;i++)raw[i]=(uint8_t)(i*17);
  for(unsigned i=0;i<81;i++){
   unsigned at=i<80?(512+i*2)*16:768*16,n=i<80?16:2048;
   uint8_t d[12]={1,0,(uint8_t)n,(uint8_t)(n>>8),(uint8_t)at,(uint8_t)(at>>8),1,0};
   for(unsigned k=0;k<4;k++)d[8+k]=(uint8_t)(token>>(8*k));
   token++;char path[80];snprintf(path,sizeof path,"tile-%04u.bin",ordinal+1);
   FILE *f=fopen(path,"wb");assert(f&&fwrite(raw,1,n,f)==n);fclose(f);
   assert(nes_sink195_bulk(&sink,d));tile_bytes+=n;
  }
 }
 return nes_sink212_seal(&sink,&candidate,&cache);
}
int main(int argc,char **argv){
 assert(argc==3);mode=argv[1];reference=!strcmp(argv[2],"reference");
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)((i*487)&0x7fff);
 nes_resident211_reset(&cache);nes_sink165_reset(&sink,exchange,NULL);
 /* Cold both banks, warmed reuse, sparse new keys, raw rows and raw exit. */
 const unsigned variants[]={0,0,0,2,2,2,3,4,5,6,7,0,0,0};
 unsigned count=0;
 unsigned total=!strcmp(mode,"pressure")?3:sizeof variants/sizeof variants[0];
 for(unsigned i=0;i<total;i++){
  bool ok=frame(variants[i],i+1);
  if(strcmp(mode,"normal")&&strcmp(mode,"pressure")&&i==1){
   assert(!ok&&sink.state==NES_SINK165_FAULT&&cache.active==0);
   if(!strcmp(mode,"wrong_display_ack"))assert(sink.error==3&&cache.open);
   nes_resident211_abort(&cache);break;
  }
  assert(ok);count++;
  if(!reference)assert(cache.displayed&&!cache.open&&cache.active==(i&1));
 }
 FILE *f=fopen("producer-done.txt","w");assert(f);fprintf(f,"%u\n",count+(!strcmp(mode,"wrong_display_ack")));fclose(f);
 printf("PASS DIRTY212 reference=%u commits=%u requests=%u packet_bytes=%u tile_bytes=%u\n",reference,count,requests,wire_bytes,tile_bytes);return 0;
}
