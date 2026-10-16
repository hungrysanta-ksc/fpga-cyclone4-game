/* SPDX-License-Identifier: MIT */
#include <windows.h>
static unsigned rpc_seq=1,qsent,qdone,qacks,retired_frames;
static uint8_t queue[4][256],qack[12];static unsigned qsizes[4];
static bool qvalid,qfault,partial_mode;
static void rpc(unsigned op,unsigned addr,const uint8_t *data,unsigned n,uint8_t *reply,unsigned want){
 char tmp[80],path[80];sprintf(tmp,"H-%06u.tmp",rpc_seq);sprintf(path,"H-%06u.req",rpc_seq);
 uint8_t h[8]={(uint8_t)op,(uint8_t)addr,(uint8_t)(addr>>8),(uint8_t)(addr>>16),(uint8_t)n,(uint8_t)(n>>8),0,0};
 FILE*f=fopen(tmp,"wb");assert(f&&fwrite(h,1,8,f)==8);if(data)assert(fwrite(data,1,n,f)==n);fclose(f);assert(!rename(tmp,path));
 sprintf(path,"H-%06u.rsp",rpc_seq++);DWORD start=GetTickCount();
 while(!(f=fopen(path,"rb"))){assert(GetTickCount()-start<120000);Sleep(1);}
 if(want)assert(fread(reply,1,want,f)==want);assert(fgetc(f)==EOF);fclose(f);
}
static void harvest208(void){
 while(qdone<qsent&&!qfault){
  char p[80];sprintf(p,"ack-%04u.bin",qdone+1);FILE*f=fopen(p,"rb");if(!f)return;
  assert(fread(qack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);uint8_t*b=queue[qdone%4];
  qvalid=true;qfault=qack[0]!=(b[0]==3?1:0)||qack[1]!=b[0]||memcmp(qack+2,b+2,8)||qack[10]!=0x65||qack[11]!=0x9a;
  assert(!qfault);if(b[0]==3)qacks++;qdone++;
 }
}
static bool joined208(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(!inside);inside=true;wire_calls++;tick++;unsigned cmd=tx[0];harvest208();
 if(cmd==0xe8||cmd==0xe9||cmd==0xea){
  if(cmd==0xea){assert(runtime.sink.displayed&&qacks==runtime.frames);retired_frames++;}
  if(partial_mode&&runtime.frames==1&&cmd==0xe9){
   uint8_t discard[259];rpc(1,0,tx,n/2,discard,n/2);rpc(6,0,NULL,0,NULL,0);inside=false;return false;
  }
  rpc(1,0,tx,n,rx,n);
 }else if(cmd==0xe1){
  assert(!qfault&&qsent-qdone<4&&n<=259);unsigned size=n-3;
  assert(size==16u+u16(tx+13)&&crc16(tx,n-2)==256u*tx[n-2]+tx[n-1]);
  memcpy(queue[qsent%4],tx+1,size);qsizes[qsent%4]=size;
  char tmp[80],name[80];sprintf(tmp,"req-%04u.tmp",qsent+1);sprintf(name,"req-%04u.bin",qsent+1);
  FILE*f=fopen(tmp,"wb");assert(f&&fwrite(tx+1,1,size,f)==size);fclose(f);assert(!rename(tmp,name));qsent++;memset(rx,0,n);
 }else if(cmd==0xe0){
  assert(n==20);memset(rx,0,n);rx[1]=0xf7;rx[2]=(qfault?128:0)|(qsent!=qdone?1:0)|(qvalid?2:0)|(qsent-qdone==4?4:0);
  rx[3]=(uint8_t)(qsent>>8);rx[4]=(uint8_t)qsent;rx[5]=(uint8_t)(qdone>>8);rx[6]=(uint8_t)qdone;
  memcpy(rx+7,qack,12);rx[19]=crc8(rx+1,18);Sleep(1);
 }else if(cmd==0xd1){
  assert(read_at<nr&&(read_at<commit_at||prepared)&&n==record_size[read_at]+3u);
  memset(rx,0,n);memcpy(rx+1,records[read_at],n-3);uint16_t c=crc16(rx+1,n-3);rx[n-2]=(uint8_t)(c>>8);rx[n-1]=(uint8_t)c;
 }else{
  assert(cmd>=0xd0&&cmd<=0xd3&&n==8);
  if(cmd==0xd2){assert(tx[2]*256u+tx[3]==(token&65535));read_at++;token++;if(read_at==nr)rpc(5,0,NULL,0,NULL,0);}
  if(cmd==0xd3){assert(read_at==commit_at&&tx[4]==1);prepared=true;}
  memset(rx,0,n);rx[1]=0xd6;bool available=read_at<nr&&(read_at<commit_at||prepared);
  rx[2]=(available?1:0)|((read_at==commit_at&&!prepared)?2:0);rx[3]=(uint8_t)(token>>8);rx[4]=(uint8_t)token;
  if(available)rx[6]=record_size[read_at];rx[7]=crc8(rx+1,6);
 }
 inside=false;return true;
}
int main(int argc,char **argv){
 assert(argc==2);partial_mode=!strcmp(argv[1],"partial");
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*371);
 token=65530;tick=0;
 assert(nes_runtime165_begin(&runtime,&received,&output,lut,joined208,ticks,guard,NULL,1000000));
 runtime.plan.poll_limit=65536;
 for(unsigned i=0;i<3;i++){
  /* Identical immutable ROM contents; fresh generation, no global reset. */
  current_scene=1;scene(2);r.generation=65534;ingress();r.generation=(uint16_t)(65534+i);
  for(unsigned j=0;j<nr;j++){records[j][2]=(uint8_t)(r.generation>>8);records[j][3]=(uint8_t)r.generation;}
  memset(sizes,0,sizeof sizes);assert(reference203_build(&r,lut,&ref,runtime.sink.displayed,stage,NULL));
  uint8_t image[162];image[0]=(uint8_t)r.generation;image[1]=(uint8_t)(r.generation>>8);
  for(unsigned t=0;t<10;t++)memcpy(image+2+t*16,r.tiles[t].data,16);
  rpc(4,0,image,sizeof image,NULL,0);
  unsigned steps=0;while(runtime.frames==i&&nes_runtime165_step(&runtime))assert(++steps<2048);
  if(partial_mode&&i==1){assert(runtime.result==NES_RUNTIME165_IO&&runtime.frames==1&&retired_frames==1);break;}
  assert(!runtime.result&&runtime.frames==i+1&&received.state==NES_NATIVE165_IDLE&&read_at==nr);
  assert(qacks==i+1&&retired_frames==i+1&&!memcmp(&ref,&output,sizeof ref));
 }
 assert(runtime.frames==(partial_mode?1u:3u));
 rpc(9,0,NULL,0,NULL,0);
 FILE*f=fopen("producer-done.txt","w");assert(f);fprintf(f,"%u\n",(unsigned)runtime.frames);fclose(f);
 printf("PASS JOIN208 frames=%u display_acks=%u retires=%u packets=%u partial=%u\n",(unsigned)runtime.frames,qacks,retired_frames,qdone,partial_mode);return 0;
}
