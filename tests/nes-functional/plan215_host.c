/* SPDX-License-Identifier: MIT */
/* Actual C200 service +207 RTL; SNES consume/display ACK are explicit fixtures. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
#include "nes_plan_service200.h"
static unsigned seq=1,frames,chunks,bytes,plans;
static uint8_t memory[160],expected[2][16384],seen[2][1024];
static struct nes_native_sink165 sink;
static struct nes_plan200 plan;
static void rpc(unsigned op,unsigned addr,const uint8_t *data,unsigned n,uint8_t *reply,unsigned want){
 char tmp[80],path[80];sprintf(tmp,"H-%06u.tmp",seq);sprintf(path,"H-%06u.req",seq);
 uint8_t h[8]={(uint8_t)op,(uint8_t)addr,(uint8_t)(addr>>8),(uint8_t)(addr>>16),(uint8_t)n,(uint8_t)(n>>8),0,0};
 FILE*f=fopen(tmp,"wb");assert(f&&fwrite(h,1,8,f)==8);if(data)assert(fwrite(data,1,n,f)==n);fclose(f);assert(!rename(tmp,path));
 sprintf(path,"H-%06u.rsp",seq++);DWORD start=GetTickCount();
 while(!(f=fopen(path,"rb"))){assert(GetTickCount()-start<120000);Sleep(1);}
 if(want)assert(fread(reply,1,want,f)==want);assert(fgetc(f)==EOF);fclose(f);
}
static unsigned le16(const uint8_t*b){return b[0]+256u*b[1];}
static bool guard(void*x){(void)x;return true;}
static bool transfer(void*x,const uint8_t*tx,uint8_t*rx,unsigned n){
 (void)x;uint8_t copy[259];assert(n<=sizeof copy);memcpy(copy,tx,n);rpc(1,0,copy,n,rx,n);
 if(copy[0]==0xe8&&rx[3]&0xfc){printf("BAD E8 frame=%u sent=%u raw=",frames,plan.sent);for(unsigned i=0;i<n;i++)printf("%02x",rx[i]);puts("");fflush(stdout);}
 return true;
}
bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){
 unsigned kind=d[1],len=le16(d+2),offset=le16(d+4),gen=le16(d+6);uint8_t b[2048],actual[12];
 assert(s==&sink&&d[0]==1&&kind<2&&len&&len<=2048&&offset+len<=sizeof expected[0]&&gen==sink.generation);
 rpc(2,0x6040,NULL,12,actual,12);assert(!memcmp(actual,d,12));rpc(2,0x400800,NULL,len,b,len);
 assert(!memcmp(b,expected[kind]+offset,len));
 unsigned stride=kind?32:16;assert(!(offset%stride)&&!(len%stride));
 for(unsigned i=0;i<len/stride;i++){unsigned slot=offset/stride+i;assert(seen[kind][slot]==1);seen[kind][slot]=2;}
 uint8_t consume[5];memcpy(consume,d+8,4);consume[4]=0xa5;rpc(3,0x604c,consume,5,NULL,0);chunks++;bytes+=len;return true;
}
static void emit(unsigned kind,unsigned slot,unsigned tag,unsigned variant){
 struct nes_plan191 q={0};q.kind=(uint8_t)kind;q.slot=(uint16_t)slot;q.tag=(uint16_t)tag;q.generation=sink.generation;
 for(unsigned i=0;i<8;i++)q.alt[i]=65535;
 if(kind<2){q.mask=kind==1&&variant?0x5a:255;for(unsigned i=0;i<16;i++)q.row[i]=(uint8_t)(variant?(7-i/2):i/2);}
 if(kind==0&&variant==2)q.alt[3]=(uint16_t)((tag+1)%10);
 unsigned k=kind==1,stride=k?32:16;assert(!seen[k][slot]);seen[k][slot]=1;
 for(unsigned i=0;i<stride;i++){
  uint8_t v=0;if(kind!=2&&i<16&&(q.mask&(1u<<(i/2)))){
   unsigned t=!(i&1)&&q.alt[i/2]!=65535?q.alt[i/2]:tag;v=memory[t*16+(i&1)*8+q.row[i]];
  }expected[k][slot*stride+i]=v;
 }
 assert(nes_plan200_emit(&plan,&q));plans++;
}
int main(void){
 static const unsigned counts[]={0,1,13,14,15,16,29,30,31,0,1,0,63,127,0,3,14,15,16,0};
 for(unsigned i=0;i<160;i++)memory[i]=(uint8_t)(i*37+11);
 plan.transfer=transfer;plan.guard=guard;plan.sink=&sink;plan.poll_limit=65536;
 for(unsigned frame=0;frame<sizeof counts/sizeof counts[0];frame++){
  uint16_t gen=(uint16_t)(65530+frame);sink.state=NES_SINK165_BUILD;sink.generation=gen;sink.displayed=false;
  memset(seen,0,sizeof seen);memset(expected,0xa5,sizeof expected);
  uint8_t image[162]={(uint8_t)gen,(uint8_t)(gen>>8)};memcpy(image+2,memory,160);rpc(4,0,image,162,NULL,0);rpc(5,0,NULL,0,NULL,0);
  emit(2,0,0,0);
  for(unsigned j=0;j<counts[frame];j++)emit(0,1+j*3,j%10,(frame+j)%3);
  if(counts[frame])for(unsigned j=0;j<5;j++)emit(1,j*7,j%10,(frame+j)%2);
  bool ok=nes_plan200_finish(&plan);if(!ok)printf("FAIL frame=%u count=%u error=%u sent=%u bytes=%u\n",frame,counts[frame],plan.error,plan.sent,plan.bytes);
  assert(ok);
  for(unsigned k=0;k<2;k++)for(unsigned j=0;j<1024;j++)assert(seen[k][j]!=1);
  /* Explicit modeled final display ACK, not a real65816/PPU claim. */
  sink.state=NES_SINK165_IDLE;sink.displayed=true;sink.last_generation=gen;assert(nes_plan200_retire(&plan));frames++;
  printf("FRAME %u gen=%u count=%u PASS\n",frame,gen,counts[frame]);fflush(stdout);
 }
 rpc(9,0,NULL,0,NULL,0);printf("PASS PLAN215 frames=%u plans=%u chunks=%u bytes=%u\n",frames,plans,chunks,bytes);return 0;
}
