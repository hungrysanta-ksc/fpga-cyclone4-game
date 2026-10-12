/* SPDX-License-Identifier: MIT */
#include "nes_native_sink165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
static struct nes_native_sink165 s;
static struct nes_native_video165 p;
static unsigned ordinal,wire_bytes;
static const char *mode;
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;char tmp[80],path[80];assert(n>=16&&n<=256&&s.state==NES_SINK165_BUSY);
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
static void scene(const char *dir,unsigned gen){
 uint8_t pattern[16384];memset(&p,0,sizeof(p));p.valid=true;p.generation=(uint16_t)gen;
 char summary[256]={0};unsigned layout,bg,obj,groups,objects,hdma,h,v;
 read_file(dir,"summary.txt",summary,sizeof(summary)-1);
 assert(sscanf(summary,"%u %u %u %u %u %u %u %u",&layout,&bg,&obj,&groups,&objects,&hdma,&h,&v)==8);
 p.bg_count=(uint16_t)bg;p.obj_count=(uint16_t)obj;p.hdma_size=(uint16_t)hdma;p.hofs[0]=(uint16_t)h;p.vofs[0]=(uint16_t)v;
 assert(nes_sink165_begin(&s,(uint16_t)gen));
 assert(read_file(dir,"bg.bin",pattern,sizeof(pattern))==bg*16);
 for(unsigned i=0;i<bg;i++)assert(nes_sink165_pattern(&s,0,i,pattern+i*16,16));
 assert(read_file(dir,"obj.bin",pattern,sizeof(pattern))==obj*32);
 for(unsigned i=0;i<obj;i++)assert(nes_sink165_pattern(&s,1,i,pattern+i*32,32));
 assert(read_file(dir,"map.bin",p.map,sizeof(p.map))==4096);
 assert(read_file(dir,"cgram.bin",p.cgram,sizeof(p.cgram))==512);
 assert(read_file(dir,"oam.bin",p.oam,sizeof(p.oam))==544);
 assert(read_file(dir,"hdma.bin",p.hdma,sizeof(p.hdma))==hdma);
 bool ok=nes_sink165_seal(&s,&p,5000);
 if(!strcmp(mode,"stop")&&gen==15){assert(!ok&&s.state==NES_SINK165_FAULT&&s.displayed);return;}
 assert(ok&&s.state==NES_SINK165_IDLE&&s.displayed);
}
static unsigned fault_mode;
static bool faulty(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;(void)n;assert(s.state==NES_SINK165_BUSY);
 /* A reentrant publish cannot start another candidate. */
 assert(!nes_sink165_begin(&s,1));
 if(fault_mode==1)return false;
 ack[0]=0;ack[1]=b[0];memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(fault_mode==2)ack[4]^=1; /* stale serial */
 if(fault_mode==3)ack[8]^=1; /* stale generation */
 if(fault_mode==4)ack[2]^=1; /* stale packet sequence */
 if(fault_mode==5)ack[0]=0xe0;
 return true;
}
int main(int argc,char **argv){
 assert(argc==4);mode=argv[3];
 for(fault_mode=1;fault_mode<=5;fault_mode++){
  nes_sink165_reset(&s,faulty,NULL);assert(!nes_sink165_begin(&s,12));
  assert(s.state==NES_SINK165_FAULT&&!nes_sink165_begin(&s,13));
 }
 nes_sink165_reset(&s,exchange,NULL);scene(argv[1],12);scene(argv[2],15);
 if(strcmp(mode,"stop")){
  scene(argv[2],16); /* true zero-delta commit, rotated candidate */
  assert(nes_sink165_begin(&s,17));
  uint8_t b[18]={2,6},ack[12];b[2]=(uint8_t)s.sequence;b[3]=(uint8_t)(s.sequence>>8);
  for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s.serial>>(i*8));
  b[8]=17;b[12]=2;s.state=NES_SINK165_BUSY;
  assert(exchange(NULL,b,sizeof(b),ack)&&ack[0]==0xe0); /* invalid section, no WRAM write */
 }
 FILE *f=fopen("producer-done.txt","w");assert(f);fprintf(f,"PASS %u %u %u\n",ordinal,wire_bytes,(unsigned)sizeof(s));fclose(f);
 printf("PASS SINK165 %s requests=%u packet_bytes=%u context=%u, 5 MCU fail-stop cases\n",mode,ordinal,wire_bytes,(unsigned)sizeof(s));return 0;
}
