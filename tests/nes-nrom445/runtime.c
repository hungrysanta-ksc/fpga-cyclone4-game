// SPDX-License-Identifier: MIT
// Exact 227 RUN with recorded RTL ingress and modeled E0/E1 queue.
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
#include "nes_native_runtime165.h"
#include "nes_palette165.inc"
static struct nes_native_runtime165 runtime;
static struct nes_native165 received;
static struct nes_native_video165 video;
static struct nes_resident211 resident;
static uint8_t queue[4][256],qack[12],chr[160];
static unsigned tokens,qsent,qdone,qacks,rpc_seq=1,retired;
static bool qvalid,qfault;
static uint32_t tick;
static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(int i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}
static void rpc(unsigned op,unsigned addr,const uint8_t *data,unsigned n,uint8_t *reply,unsigned want){
 char tmp[80],path[80];sprintf(tmp,"H-%06u.tmp",rpc_seq);sprintf(path,"H-%06u.req",rpc_seq);
 uint8_t h[8]={(uint8_t)op,(uint8_t)addr,(uint8_t)(addr>>8),(uint8_t)(addr>>16),(uint8_t)n,(uint8_t)(n>>8),0,0};
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(h,1,8,f)==8);if(data)assert(fwrite(data,1,n,f)==n);fclose(f);assert(rename(tmp,path)==0);
 sprintf(path,"H-%06u.rsp",rpc_seq++);DWORD start=GetTickCount();while(!(f=fopen(path,"rb"))){assert(GetTickCount()-start<120000);Sleep(1);}
 if(want)assert(fread(reply,1,want,f)==want);assert(fgetc(f)==EOF);fclose(f);
}
static void harvest(void){
 while(qdone<qsent&&!qfault){char path[80];sprintf(path,"ack-%04u.bin",qdone+1);FILE *f=fopen(path,"rb");if(!f)return;
  assert(fread(qack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);uint8_t *b=queue[qdone%4];qvalid=true;
  qfault=qack[0]!=(b[0]==3?1:0)||qack[1]!=b[0]||memcmp(qack+2,b+2,8)||qack[10]!=0x65||qack[11]!=0x9a;assert(!qfault);if(b[0]==3)qacks++;qdone++;
 }
}
static uint32_t ticks(void *p){(void)p;return tick++;}
static bool service(void *p){(void)p;return true;}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;unsigned cmd=tx[0];harvest();
 if(cmd==0xe8||cmd==0xe9||cmd==0xea){if(cmd==0xea){DWORD began=GetTickCount();while(qacks<runtime.frames){harvest();assert(GetTickCount()-began<30000);Sleep(1);}assert(runtime.sink.displayed);retired++;}rpc(1,0,tx,n,rx,n);}
 else if(cmd==0xe1){
  assert(!qfault&&qsent-qdone<4&&n<=259);unsigned size=n-3;assert(size==16u+tx[13]+256u*tx[14]&&crc16(tx,n-2)==256u*tx[n-2]+tx[n-1]);
  const uint8_t *b=tx+1;if(b[0]==3){char oamname[40];sprintf(oamname,"oam-%u.bin",received.generation);FILE *of=fopen(oamname,"wb");assert(of&&fwrite(video.oam,1,sizeof video.oam,of)==sizeof video.oam);fclose(of);}if(b[0]==7){unsigned len=b[14]+256u*b[15];uint8_t raw[2048];assert(len&&len<=sizeof raw);rpc(2,0x400800,NULL,len,raw,len);char tile[80];sprintf(tile,"tile-%04u.bin",qsent+1);FILE *f=fopen(tile,"wb");assert(f&&fwrite(raw,1,len,f)==len);fclose(f);}
  memcpy(queue[qsent%4],b,size);char tmp[80],path[80];sprintf(tmp,"req-%04u.tmp",qsent+1);sprintf(path,"req-%04u.bin",qsent+1);FILE *f=fopen(tmp,"wb");assert(f&&fwrite(b,1,size,f)==size);fclose(f);rpc(1,0,tx,n,rx,n);assert(rename(tmp,path)==0);qsent++;
 }else if(cmd==0xe0){
  assert(n==20);rpc(1,0,tx,n,rx,n);Sleep(1);
 }else{
  assert(cmd>=0xd0&&cmd<=0xd3);rpc(1,0,tx,n,rx,n);
  if(cmd==0xd2){tokens++;if(received.state==NES_NATIVE165_COMMITTED)rpc(5,0,NULL,0,NULL,0);}
 }

 return true;
}
int main(int argc,char **argv){
 assert(argc==3);FILE *f;
 f=fopen(argv[2],"rb");assert(f&&fseek(f,16400,SEEK_SET)==0&&fread(chr,1,160,f)==160);fclose(f);uint8_t image[162]={4,0};memcpy(image+2,chr,160);rpc(4,0,image,162,NULL,0);
 assert(nes_runtime165_begin(&runtime,&received,&video,native_palette165,transfer,ticks,service,NULL,1000000,&resident,1,true));
 unsigned steps=0;uint16_t first_gen=0,second_gen=0;
 while(runtime.frames<2 && nes_runtime165_step(&runtime)){
  assert(++steps<6000);if(runtime.frames==1&&!first_gen){first_gen=runtime.generation;printf("LIVE frame1 generation=%u token=%u\n",first_gen,tokens);fflush(stdout);}
 }
 second_gen=runtime.generation;
 if(runtime.result||runtime.frames!=2||received.state!=NES_NATIVE165_IDLE||qacks!=2||retired!=2||!tokens){fprintf(stderr,"RUN diagnostic result=%u receiver=%u video=%u sink=%u frames=%u qsent=%u qdone=%u qfault=%u token=%u\n",runtime.result,runtime.receiver_error,runtime.video_error,runtime.sink.error,(unsigned)runtime.frames,qsent,qdone,qfault,tokens);return 2;}
 rpc(9,0,NULL,0,NULL,0);f=fopen("producer-done.txt","w");assert(f);fprintf(f,"2\n");fclose(f);
 printf("PASS NROM445 live two RUN frames=%u steps=%u SPI=%u packets=%u final_ack=%u retire=%u tokens=%u gen=%u,%u\n",(unsigned)runtime.frames,steps,(unsigned)runtime.transactions,qdone,qacks,retired,tokens,first_gen,second_gen);return 0;
}
