/* SPDX-License-Identifier: MIT */
#include "nes_native_stage165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native_stage165 s;
static struct nes_native_video165 p;
/* HOST model of SNES bank7F; never part of firmware static RAM. */
static uint8_t wram[65536],saved[32768],pattern[16384];
static unsigned reads,writes,bad_read,bad_write;
static bool rd(void *ctx,uint32_t a,uint8_t *b,unsigned n){
 (void)ctx;assert(n&&n<=64&&a>=0x7f0000&&a+n<=0x800000);reads++;
 if(reads==bad_read)return false;
 memcpy(b,wram+a-0x7f0000,n);return true;
}
static bool wr(void *ctx,uint32_t a,const uint8_t *b,unsigned n){
 (void)ctx;assert(n&&n<=64&&a>=0x7f0000&&a+n<=0x800000);writes++;
 assert(!s.displayed||(a-0x7f0000)/32768!=s.current);
 if(writes==bad_write)return false;
 memcpy(wram+a-0x7f0000,b,n);return true;
}
static void read_file(const char *dir,const char *name,void *b,unsigned n){
 char path[1024];assert(snprintf(path,sizeof(path),"%s/%s",dir,name)>0);
 FILE *f=fopen(path,"rb");assert(f&&fread(b,1,n,f)==n&&fgetc(f)==EOF);fclose(f);
}
static void finish(void){
 unsigned steps=0;while(s.state==NES_STAGE165_DIFF){unsigned r=reads;assert(nes_stage165_step(&s));assert(reads-r<=2);assert(++steps<500);}
 assert(s.state==NES_STAGE165_READY);
}
static void begin(unsigned gen){assert(nes_stage165_begin(&s,(uint16_t)gen));}
static void patterns(unsigned bg,unsigned obj){
 for(unsigned i=0;i<bg;i++)assert(nes_stage165_pattern(&s,0,i,pattern+i*16,16));
 for(unsigned i=0;i<obj;i++)assert(nes_stage165_pattern(&s,1,i,pattern+i*32,32));
}
static void ack(void){assert(nes_stage165_arm(&s));assert(nes_stage165_ack(&s,s.serial,s.generation,true));}
static void synthetic(void){
 memset(&p,0,sizeof(p));memset(pattern,0,sizeof(pattern));p.valid=true;p.bg_count=1;p.hdma_size=1;p.generation=7;
 begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();ack();
}
int main(int argc,char **argv){
 assert(argc==3);nes_stage165_reset(&s,rd,wr,NULL);memset(wram,0xcd,sizeof(wram));
 FILE *commands=fopen("commands.tsv","w");assert(commands);
 for(unsigned frame=0;frame<2;frame++){
  char path[1024];snprintf(path,sizeof(path),"%s/summary.txt",argv[frame+1]);FILE *f=fopen(path,"r");assert(f);
  unsigned size,bg,obj,groups,objects,hdma,h,v;assert(fscanf(f,"%u%u%u%u%u%u%u%u",&size,&bg,&obj,&groups,&objects,&hdma,&h,&v)==8);fclose(f);
  memset(&p,0,sizeof(p));p.valid=true;p.generation=(uint16_t)(12+frame*3);p.bg_count=(uint16_t)bg;p.obj_count=(uint16_t)obj;p.hdma_size=(uint16_t)hdma;p.hofs[0]=(uint16_t)h;p.vofs[0]=(uint16_t)v;
  begin(p.generation);read_file(argv[frame+1],"bg.bin",pattern,bg*16);
  for(unsigned i=0;i<bg;i++)assert(nes_stage165_pattern(&s,0,i,pattern+i*16,16));
  read_file(argv[frame+1],"obj.bin",pattern,obj*32);
  for(unsigned i=0;i<obj;i++)assert(nes_stage165_pattern(&s,1,i,pattern+i*32,32));
  read_file(argv[frame+1],"map.bin",p.map,4096);read_file(argv[frame+1],"cgram.bin",p.cgram,512);read_file(argv[frame+1],"oam.bin",p.oam,544);read_file(argv[frame+1],"hdma.bin",p.hdma,hdma);
  unsigned before=reads;assert(nes_stage165_seal(&s,&p,5000));finish();
  fprintf(commands,"H %u %u %u %u %u %u %u %u\n",frame,s.serial,s.generation,s.payload,s.charged,s.ncommands,h,v);
  for(unsigned i=0;i<s.ncommands;i++){struct nes_stage165_command *c=&s.commands[i];fprintf(commands,"C %u %u %u %u\n",c->kind,(unsigned)c->source,c->dest,c->size);}
  snprintf(path,sizeof(path),"wram%u.bin",frame);f=fopen(path,"wb");assert(f&&fwrite(wram,1,sizeof(wram),f)==sizeof(wram));fclose(f);
  assert(nes_stage165_arm(&s));assert(!nes_stage165_begin(&s,77));assert(!nes_stage165_ack(&s,s.serial-1,s.generation,true));assert(s.state==NES_STAGE165_WAIT);
  assert(!nes_stage165_ack(&s,s.serial,(uint16_t)(s.generation+1),true));assert(nes_stage165_ack(&s,s.serial,s.generation,true));
  assert(!nes_stage165_ack(&s,s.serial,s.generation,true));
  printf("FRAME %u payload=%u commands=%u reads=%u\n",frame,(unsigned)s.payload,s.ncommands,reads-before);
 }
 fclose(commands);unsigned rejects=0;
 memcpy(saved,wram+s.current*32768,32768);begin(123);bad_write=writes+1;
 assert(!nes_stage165_pattern(&s,0,0,pattern,16)&&s.state==NES_STAGE165_FAILED);rejects++;bad_write=0;nes_stage165_abort(&s);
 assert(!memcmp(saved,wram+s.current*32768,32768));
 begin(123);assert(!nes_stage165_pattern(&s,0,1,pattern,16));rejects++;nes_stage165_abort(&s);
 begin(123);assert(!nes_stage165_seal(&s,&p,5000));rejects++;nes_stage165_abort(&s);
 nes_stage165_reset(&s,rd,wr,NULL);synthetic();
 /* No-op still waits for ACK; staged bytes never overwrite displayed slot. */
 begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(!s.ncommands);ack();
 /* Two dirty words across a 64-byte step boundary become one command. */
 p.map[62]=1;p.map[66]=2;begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(s.ncommands==1&&s.payload==6&&s.commands[0].dest==0x803e);ack();
 /* Shrink then regrow must upload new tail even if stale bytes match. */
 p.bg_count=2;begin(7);patterns(2,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(s.payload==16);ack();
 p.bg_count=1;begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();ack();
 p.bg_count=2;begin(7);patterns(2,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(s.payload==16);ack();
 begin(7);patterns(2,0);assert(nes_stage165_seal(&s,&p,5000));bad_read=reads+1;
 assert(!nes_stage165_step(&s)&&s.state==NES_STAGE165_FAILED);rejects++;bad_read=0;nes_stage165_abort(&s);
 p.map[0]^=1;begin(7);patterns(2,0);assert(nes_stage165_seal(&s,&p,1));while(s.state==NES_STAGE165_DIFF)nes_stage165_step(&s);assert(s.state==NES_STAGE165_FAILED&&s.error==5);rejects++;nes_stage165_abort(&s);
 for(unsigned i=0;i<33;i++)p.map[128+i*64]^=1;
 begin(7);patterns(2,0);assert(nes_stage165_seal(&s,&p,65535));while(s.state==NES_STAGE165_DIFF)nes_stage165_step(&s);assert(s.state==NES_STAGE165_FAILED&&s.error==4);rejects++;nes_stage165_abort(&s);
 nes_stage165_reset(&s,rd,wr,NULL);synthetic();
 begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(nes_stage165_arm(&s));nes_stage165_abort(&s);
 assert(s.state==NES_STAGE165_FAULT&&!nes_stage165_begin(&s,8));rejects++;
 nes_stage165_reset(&s,rd,wr,NULL);synthetic();begin(7);patterns(1,0);assert(nes_stage165_seal(&s,&p,5000));finish();assert(nes_stage165_arm(&s));
 assert(!nes_stage165_ack(&s,s.serial,s.generation,false)&&s.state==NES_STAGE165_FAULT);rejects++;
 nes_stage165_reset(&s,rd,wr,NULL);s.serial=UINT32_MAX;assert(!nes_stage165_begin(&s,7));rejects++;
 printf("PASS STAGE165 storage=%u rejects=%u WRAM_ONLY bank7F no_cartridge_memory\n",(unsigned)sizeof(s),rejects);return 0;
}
