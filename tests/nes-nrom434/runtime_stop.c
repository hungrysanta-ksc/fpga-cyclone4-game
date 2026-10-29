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
static uint8_t blocks[128][256],queue[4][256],qack[12],chr[160];
static unsigned lengths[128],nblocks,index_block,token,qsent,qdone,qacks,rpc_seq=1,retired;
static bool prepared,qvalid,qfault,injected;
static uint32_t tick;
static uint8_t crc8(const uint8_t *b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(int i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
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
 if(cmd==0xe9&&!injected){uint8_t discard[259];assert(n>2);rpc(1,0,tx,n/2,discard,n/2);rpc(6,0,NULL,0,NULL,0);injected=true;return false;}
 if(cmd==0xe8||cmd==0xe9||cmd==0xea){if(cmd==0xea){assert(runtime.sink.displayed&&qacks==1);retired++;}rpc(1,0,tx,n,rx,n);}
 else if(cmd==0xe1){
  assert(!qfault&&qsent-qdone<4&&n<=259);unsigned size=n-3;assert(size==16u+tx[13]+256u*tx[14]&&crc16(tx,n-2)==256u*tx[n-2]+tx[n-1]);
  const uint8_t *b=tx+1;if(b[0]==3){FILE *of=fopen("oam-4.bin","wb");assert(of&&fwrite(video.oam,1,sizeof video.oam,of)==sizeof video.oam);fclose(of);}if(b[0]==7){unsigned len=b[14]+256u*b[15];uint8_t raw[2048];assert(len&&len<=sizeof raw);rpc(2,0x400800,NULL,len,raw,len);char tile[80];sprintf(tile,"tile-%04u.bin",qsent+1);FILE *f=fopen(tile,"wb");assert(f&&fwrite(raw,1,len,f)==len);fclose(f);}
  memcpy(queue[qsent%4],b,size);char tmp[80],path[80];sprintf(tmp,"req-%04u.tmp",qsent+1);sprintf(path,"req-%04u.bin",qsent+1);FILE *f=fopen(tmp,"wb");assert(f&&fwrite(b,1,size,f)==size);fclose(f);assert(rename(tmp,path)==0);qsent++;memset(rx,0,n);
 }else if(cmd==0xe0){
  assert(n==20);memset(rx,0,n);rx[1]=0xf7;rx[2]=(qfault?128:0)|(qsent!=qdone?1:0)|(qvalid?2:0)|(qsent-qdone==4?4:0);rx[3]=(uint8_t)(qsent>>8);rx[4]=(uint8_t)qsent;rx[5]=(uint8_t)(qdone>>8);rx[6]=(uint8_t)qdone;memcpy(rx+7,qack,12);rx[19]=crc8(rx+1,18);Sleep(1);
 }else if(cmd==0xd1){
  assert(index_block<nblocks&&(index_block<nblocks-1||prepared)&&n==lengths[index_block]+3);memset(rx,0,n);memcpy(rx+1,blocks[index_block],n-3);uint16_t c=crc16(rx+1,n-3);rx[n-2]=(uint8_t)(c>>8);rx[n-1]=(uint8_t)c;
 }else{
  assert(cmd>=0xd0&&cmd<=0xd3&&n==8);
  if(cmd==0xd2){assert(tx[2]*256u+tx[3]==token);index_block++;token++;if(index_block==nblocks)rpc(5,0,NULL,0,NULL,0);}
  if(cmd==0xd3){assert(index_block==nblocks-1&&tx[4]==1);prepared=true;}
  memset(rx,0,n);rx[1]=0xd6;bool available=index_block<nblocks&&(index_block<nblocks-1||prepared);rx[2]=(available?1:0)|((index_block==nblocks-1&&!prepared)?2:0);rx[3]=(uint8_t)(token>>8);rx[4]=(uint8_t)token;if(available){rx[5]=(uint8_t)(lengths[index_block]>>8);rx[6]=(uint8_t)lengths[index_block];}rx[7]=crc8(rx+1,6);
 }
 return true;
}
int main(int argc,char **argv){
 assert(argc==3);FILE *f=fopen(argv[1],"r");assert(f);char hex[513];unsigned tok,n;
 while(fscanf(f,"%u %u %512s",&tok,&n,hex)==3){assert(tok==nblocks&&n&&n<=256&&strlen(hex)==2*n&&nblocks<128);lengths[nblocks]=n;for(unsigned i=0;i<n;i++){unsigned v;assert(sscanf(hex+2*i,"%2x",&v)==1);blocks[nblocks][i]=(uint8_t)v;}nblocks++;}assert(feof(f)&&nblocks==25);fclose(f);
 f=fopen(argv[2],"rb");assert(f&&fseek(f,16400,SEEK_SET)==0&&fread(chr,1,160,f)==160);fclose(f);uint8_t image[162]={4,0};memcpy(image+2,chr,160);rpc(4,0,image,162,NULL,0);
 assert(nes_runtime165_begin(&runtime,&received,&video,native_palette165,transfer,ticks,service,NULL,1000000,&resident,1,true));
 unsigned steps=0;while(!runtime.frames&&nes_runtime165_step(&runtime))assert(++steps<2000);
 assert(injected && runtime.result==NES_RUNTIME165_IO && runtime.frames==0 && qacks==0 && retired==0 && resident.fault && !resident.open);
 DWORD began=GetTickCount();while(qdone<qsent){harvest();assert(GetTickCount()-began<30000);Sleep(1);}rpc(9,0,NULL,0,NULL,0);
 f=fopen("producer-done.txt","w");assert(f);fprintf(f,"0\n");fclose(f);
 printf("PASS NROM436 partial E9 STOP frames=%u result=%u packets=%u final_ack=%u retire=%u\n",(unsigned)runtime.frames,runtime.result,qdone,qacks,retired);return 0;
}
