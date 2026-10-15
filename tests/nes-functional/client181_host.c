/* SPDX-License-Identifier: MIT */
/* Real paired C sink + real65816 ACKs over a held file mailbox. */
#include "nes_native_sink165.h"
#include "nes_sink_trace168.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
static struct nes_native_sink165 sink;
static struct nes_native_video165 p;
static unsigned ordinal,wire_bytes;
static const char *mode;
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static bool exchange(void *ctx,const uint8_t *data,unsigned n,uint8_t ack[12]){
 (void)ctx;char tmp[80],path[80];uint8_t b[256];memcpy(b,data,n);
 assert(sink.state==NES_SINK165_BUSY);
 if(get16(b+8)==13&&b[0]==3){
  if(!strcmp(mode,"version"))b[36]^=1;
  if(!strcmp(mode,"count"))b[38]=8;
  if(!strcmp(mode,"count_mismatch"))b[38]=6;
  if(!strcmp(mode,"seal_size")){b[12]=20;n-=4;}
 }
 if(get16(b+8)==13&&b[0]==2&&b[1]==5){
  unsigned at=get16(b+10),size=get16(b+12),offset=0,value=0;
  if(!strcmp(mode,"mode")){offset=3169+1;value=7;}
  if(!strcmp(mode,"repeat")){offset=3169;value=128;}
  if(!strcmp(mode,"length")){offset=3412;value=80;}
  if(!strcmp(mode,"terminator")){offset=3250+60;value=1;}
  if(!strcmp(mode,"scroll")){offset=0;value=128;}
  if(offset>=at&&offset<at+size&&value)b[16+offset-at]=(uint8_t)value;
 }
 ordinal++;wire_bytes+=n;snprintf(tmp,sizeof(tmp),"req-%04u.tmp",ordinal);snprintf(path,sizeof(path),"req-%04u.bin",ordinal);
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(b,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 snprintf(path,sizeof(path),"ack-%04u.bin",ordinal);DWORD started=GetTickCount();
 do {f=fopen(path,"rb");if(f)break;Sleep(1);}while(GetTickCount()-started<15000);
 if(!f)return false;
 assert(fread(ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);return true;
}
static unsigned read_file(const char *dir,const char *name,void *b,unsigned max){
 char path[1024];assert(snprintf(path,sizeof(path),"%s/%s",dir,name)>0);
 FILE *f=fopen(path,"rb");assert(f);unsigned n=(unsigned)fread(b,1,max,f);assert(fgetc(f)==EOF);fclose(f);return n;
}
static bool scene(const char *root,const char *fixture,unsigned gen,unsigned count,unsigned mask){
 char dir[1024],summary[256]={0};uint8_t pattern[16384];unsigned layout,bg,obj,groups,objects,hdma,h,v;
 assert(snprintf(dir,sizeof(dir),"%s/%s",root,fixture)>0);
 memset(&p,0,sizeof(p));p.valid=true;p.generation=(uint16_t)gen;p.patch_count=(uint8_t)count;p.display_mask=(uint8_t)mask;
 read_file(dir,"summary.txt",summary,sizeof(summary)-1);
 assert(sscanf(summary,"%u %u %u %u %u %u %u %u",&layout,&bg,&obj,&groups,&objects,&hdma,&h,&v)==8);
 assert(layout==sizeof(p));p.bg_count=(uint16_t)bg;p.obj_count=(uint16_t)obj;p.hdma_size=(uint16_t)hdma;p.hofs[0]=(uint16_t)h;p.vofs[0]=(uint16_t)v;
 assert(nes_sink165_begin(&sink,(uint16_t)gen));
 assert(read_file(dir,"bg.bin",pattern,sizeof(pattern))==bg*16);
 if(!strcmp(mode,"max")){for(unsigned i=bg*16;i<16384;i++)pattern[i]=pattern[i%(bg*16)];bg=1024;p.bg_count=1024;}
 for(unsigned i=0;i<bg;){unsigned n=bg-i;if(n>15)n=15;assert(nes_sink165_pattern(&sink,0,i,pattern+i*16,n*16));i+=n;}
 assert(read_file(dir,"obj.bin",pattern,sizeof(pattern))==obj*32);
 if(!strcmp(mode,"max")){for(unsigned i=obj*32;i<4096;i++)pattern[i]=pattern[i%(obj*32)];obj=128;p.obj_count=128;}
 for(unsigned i=0;i<obj;){unsigned n=obj-i;if(n>7)n=7;assert(nes_sink165_pattern(&sink,1,i,pattern+i*32,n*32));i+=n;}
 assert(read_file(dir,"map.bin",p.map,sizeof(p.map))==4096);
 assert(read_file(dir,"cgram.bin",p.cgram,sizeof(p.cgram))==512);
 assert(read_file(dir,"oam.bin",p.oam,sizeof(p.oam))==544);
 assert(read_file(dir,"hdma.bin",p.hdma,sizeof(p.hdma))==hdma);
 if(count){
  assert(read_file(dir,"raw.bin",p.patch.chr,2048)==2048);
  p.patch.size[0]=(uint16_t)read_file(dir,"mode-a.bin",p.patch.mode[0],81);
  p.patch.size[1]=(uint16_t)read_file(dir,"mode-b.bin",p.patch.mode[1],81);
  p.patch.size[2]=(uint16_t)read_file(dir,"enable.bin",p.patch.enable,81);
 }
 return nes_sink165_seal(&sink,&p,5000);
}
int main(int argc,char **argv){
 assert(argc==3);mode=argv[2];nes_sink165_reset(&sink,exchange,NULL);
 bool raw_first=!strcmp(mode,"raw_first");
 assert(scene(argv[1],raw_first?"rows7-phase0":"rows0-phase0",12,raw_first?7:0,0x1e));
 bool ok=scene(argv[1],raw_first?"rows0-phase0":"rows7-phase0",13,raw_first?0:7,0x1e);
 if(!strcmp(mode,"max")||raw_first){assert(ok);}
 else if(strcmp(mode,"normal")){
  assert(!ok&&sink.state==NES_SINK165_FAULT&&sink.displayed);
  assert(nes_sink_trace168.ack[0]==(!strncmp(mode,"stop",4)?0xe4:0xe0));
 }else{
  assert(ok);
  assert(scene(argv[1],"rows7-phase1",14,7,0x18));
  assert(scene(argv[1],"rows0-phase0",15,0,0x1e));
  assert(scene(argv[1],"rows0-phase0",16,0,0x1e));
  assert(scene(argv[1],"rows1-phase0",17,1,0x1e));
  assert(scene(argv[1],"rows7-phase2",18,7,0x18));
 }
 FILE *f=fopen("producer-done.txt","w");assert(f);fprintf(f,"PASS %u %u\n",ordinal,wire_bytes);fclose(f);
 printf("PASS CLIENT181 %s requests=%u bytes=%u\n",mode,ordinal,wire_bytes);return 0;
}
