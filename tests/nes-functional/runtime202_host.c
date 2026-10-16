/* SPDX-License-Identifier: MIT */
/* Actual receiver/planner/service/sink/window/RUN. Only hardware is modeled.
 * Reuse the established eight geometry fixtures and reference converter. */
#define main plan191_fixture_main
#include "plan191_host.c"
#undef main
#include "nes_native_runtime165.h"
static struct nes_native165 received;
static struct nes_native_video165 output;
static struct nes_native_runtime165 runtime;
static uint8_t records[2048][12],record_size[2048];
static unsigned nr,read_at,token,commit_at,wire_calls,services,mode;
static bool prepared,inside,ended,retiring;
static unsigned accepted,retire_delay,retire_calls,final_acks,bulk_count;
static unsigned window_sent,window_done;static uint8_t window_ack[12];
static uint8_t descriptors[16][12],pixels[16][32];static unsigned used,head;
static uint32_t tick,chunk_token;
static unsigned u16(const uint8_t *b){return b[0]+256u*b[1];}
static uint8_t crc8(const uint8_t *b,unsigned n){uint8_t c=0;while(n--){c^=*b++;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);}return c;}
static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}
static void record(unsigned k,unsigned i,uint64_t v){
 static const unsigned widths[]={2,1,7,4,7,1,2,8};unsigned n=widths[k];assert(nr<2048);
 uint8_t *b=records[nr];unsigned tag=k*8192+i;b[0]=(uint8_t)(tag>>8);b[1]=(uint8_t)tag;
 b[2]=(uint8_t)(r.generation>>8);b[3]=(uint8_t)r.generation;
 for(unsigned j=0;j<n;j++)b[4+j]=(uint8_t)(v>>(8*(n-1-j)));
 record_size[nr++]=(uint8_t)(4+n);
}
static void ingress(void){
 nr=read_at=0;prepared=false;
 record(7,0,(UINT64_C(0x1813)<<48)|((uint64_t)(r.counts[0]/33)<<42)|((uint64_t)(r.counts[5]/32)<<36)|
  (UINT64_C(224)<<28)|((uint64_t)r.counts[2]<<20)|((uint64_t)r.counts[3]<<12)|r.patch_count);
 for(unsigned k=0;k<6;k++)for(unsigned i=0;i<r.counts[k];){
  if(k==1||k==5){uint64_t v=0;unsigned n=r.counts[k]-i;if(n>8)n=8;
   for(unsigned j=0;j<n;j++)v=(v<<8)|(k==1?r.rows[i+j]:r.palette[i+j]);
   record(7,0x1800+k*256+n-1,v);i+=n;
  }else{uint64_t v=k==0?r.maps[i]:k==2?r.objects[i]:k==3?r.exceptions[i]:r.raster[i];record(k,i++,v);}
 }
 for(unsigned t=0;t<r.ntiles;t++)for(unsigned lane=0;lane<16;lane++)
  record(6,r.tiles[t].tag,(r.tiles[t].kind<<12)|(lane<<8)|r.tiles[t].data[lane]);
 unsigned logical=0;for(unsigned k=0;k<6;k++)logical+=r.counts[k];logical+=r.ntiles*16;
 unsigned bytes=r.ntiles*16;record(7,4,((uint64_t)logical<<16)|bytes);
 for(unsigned i=0;i<r.patch_count*256u;){unsigned n=r.patch_count*256u-i;if(n>10)n=10;uint64_t v=0;
  for(unsigned j=0;j<n;j++)v=(v<<6)|r.raw_pixels[i+j];
  record(7,0x1000+i,v|((uint64_t)n<<60));i+=n;logical+=n;bytes+=n;
 }
 record(7,1,((uint64_t)logical<<16)|bytes);commit_at=nr;record(7,3,0);
}
static uint32_t ticks(void *ctx){(void)ctx;return tick;}
static bool guard(void *ctx){(void)ctx;assert(!inside);services++;return !(mode==3&&bulk_count);}
static void decode(const uint8_t *b,unsigned n,unsigned plans_count){
 unsigned at=0;used=head=0;accepted++;
 for(unsigned i=0;i<plans_count;i++){
  unsigned kind,gen,slot=0,tag=0,mask=0,rows[16]={0},alt[8],size;
  for(unsigned f=0;f<8;f++)alt[f]=65535;
  const uint8_t *p=b+at;
  if(p[0]&128){kind=p[0]&3;gen=u16(p+1);size=kind>=2?3:kind==1?8:7;
   if(kind<2){slot=u16(p+3);tag=u16(p+5);mask=kind==1?p[7]:255;for(unsigned f=0;f<16;f++)rows[f]=f/2;}
  }else{kind=p[0];gen=u16(p+2);slot=u16(p+4);tag=u16(p+6);mask=p[8];size=16;
   uint64_t packed=0;for(unsigned j=0;j<6;j++)packed|=(uint64_t)p[9+j]<<(8*j);
   for(unsigned f=0;f<16;f++)rows[f]=(unsigned)(packed>>(f*3))&7;
   for(unsigned f=0;f<8;f++)if(p[1]&(1u<<f)){alt[f]=u16(p+size);size+=2;}
  }
  at+=size;assert(at<=n&&gen==r.generation);
  if(kind==3){assert(i+1==plans_count);ended=true;continue;}
  assert(used<16);unsigned unit=kind==1?32:16;uint8_t *d=descriptors[used],*out=pixels[used];memset(d,0,12);memset(out,0,32);
  d[0]=1;d[1]=kind==1;d[2]=(uint8_t)unit;d[4]=(uint8_t)(slot*unit);d[5]=(uint8_t)(slot*unit>>8);
  d[6]=(uint8_t)gen;d[7]=(uint8_t)(gen>>8);for(unsigned j=0;j<4;j++)d[8+j]=(uint8_t)(chunk_token>>(8*j));chunk_token++;
  if(kind<2){assert(tag<r.ntiles);for(unsigned f=0;f<8;f++)if(mask&(1u<<f)){
   unsigned low=alt[f]==65535?tag:alt[f];assert(low<r.ntiles);
   out[f*2]=r.tiles[low].data[rows[f*2]];out[f*2+1]=r.tiles[tag].data[8+rows[f*2+1]];
  }}
  assert(slot*unit+unit<=sizes[kind==1]);assert(!memcmp(out,(kind==1?obj:bg)+slot*unit,unit));used++;
 }
 assert(at==n);
}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;assert(!inside);inside=true;wire_calls++;tick++;
 unsigned cmd=tx[0];
 if(cmd==0xe9){unsigned len=u16(tx+1);assert(tx==rx&&n==len+8&&tx[n-1]==0xa5&&!used&&!ended);
  assert(crc8(tx,n-2)==tx[n-2]&&crc16(tx+4,len)==256u*tx[len+4]+tx[len+5]);
  decode(tx+4,len,tx[3]);memset(rx,0xa7,n);
 }else if(cmd==0xe1){
  const uint8_t *p=tx+1;assert(n>=19&&crc16(tx,n-2)==256u*tx[n-2]+tx[n-1]);
  assert(received.state==NES_NATIVE165_COMMITTED&&u16(p+8)==r.generation);
  if(p[0]==7){assert(used&&!memcmp(p+16,descriptors[head]+8,4));used--;head++;bulk_count++;}
  else if(p[0]==3){assert(ended&&!used&&runtime.plan.finished);final_acks++;}
  else assert(p[0]==1||p[1]>=2); /* BG/OBJ must never use old DATA upload. */
  window_sent++;window_done=window_sent;window_ack[0]=p[0]==3?1:0;window_ack[1]=p[0];memcpy(window_ack+2,p+2,8);window_ack[10]=0x65;window_ack[11]=0x9a;
  if(mode==1&&p[0]==3)window_ack[10]^=1;
  if(mode==2&&p[0]==7)tick=runtime.started+runtime.limit;
  memset(rx,0,n);
 }else if(cmd==0xea){
  assert(n==7&&tx[5]==crc8(tx,5)&&tx[6]==0xa5&&u16(tx+1)==r.generation&&tx[3]*256u+tx[4]==accepted);
  assert(ended&&!used&&runtime.sink.displayed&&runtime.sink.last_generation==r.generation&&received.state==NES_NATIVE165_COMMITTED);
  retiring=true;retire_delay=3;retire_calls++;memset(rx,0,n);
 }else if(cmd==0xd1){
  assert(read_at<nr&&(read_at<commit_at||prepared)&&n==record_size[read_at]+3u);
  memset(rx,0,n);memcpy(rx+1,records[read_at],n-3);uint16_t c=crc16(rx+1,n-3);rx[n-2]=(uint8_t)(c>>8);rx[n-1]=(uint8_t)c;
  if(mode==6&&read_at==2)rx[n-1]^=1;
 }else{
  if(cmd==0xd2){assert(u16((uint8_t[]){tx[3],tx[2]})==(token&65535));read_at++;token++;}
  if(cmd==0xd3){assert(read_at==commit_at&&tx[4]==1);prepared=true;}
  memset(rx,0,n);
  if(cmd>=0xd0&&cmd<=0xd3){
   assert(n==8);rx[1]=0xd6;bool available=read_at<nr&&(read_at<commit_at||prepared);
   rx[2]=(available?1:0)|((read_at==commit_at&&!prepared)?2:0);rx[3]=(uint8_t)(token>>8);rx[4]=(uint8_t)token;
   if(available)rx[6]=record_size[read_at];
   rx[7]=crc8(rx+1,6);
  }else if(cmd==0xe0){
   assert(n==20);rx[1]=0xf7;rx[2]=window_sent?2:0;rx[3]=rx[5]=(uint8_t)(window_sent>>8);rx[4]=rx[6]=(uint8_t)window_sent;
   memcpy(rx+7,window_ack,12);rx[19]=crc8(rx+1,18);
  }else{
   assert(cmd==0xe8&&n==20);rx[1]=0xd7;rx[2]=4;rx[3]=(used||ended?0:1)|(ended?2:0)|(retiring?4:0);
   rx[4]=(uint8_t)(accepted>>8);rx[5]=(uint8_t)accepted;if(used)memcpy(rx+6,descriptors[head],12);
   if(retiring&&mode!=4&&!--retire_delay){retiring=ended=false;accepted=0;}
   if(mode==5&&used)rx[6+6]^=1;
   rx[19]=crc8(rx+1,18);
  }
 }
 inside=false;return true;
}
static void init(void){
 wire_calls=services=window_sent=window_done=accepted=retire_calls=final_acks=bulk_count=used=head=0;
 token=65530;chunk_token=1000;ended=retiring=inside=false;tick=UINT32_MAX-20;memset(window_ack,0,12);
 assert(nes_runtime165_begin(&runtime,&received,&output,lut,transfer,ticks,guard,NULL,1000000));runtime.plan.poll_limit=16;
}
static void build(unsigned variant,unsigned gen){
 scene(variant);r.generation=(uint16_t)gen;memset(sizes,0,sizeof sizes);
 assert(nes_native_video185_build(&r,lut,&ref,runtime.sink.displayed,stage,NULL));ingress();
}
int main(void){
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*371);
 mode=0;init();
 unsigned sequence[]={0,2,3,7,0,0,2,7,0};
 for(unsigned i=0;i<sizeof(sequence)/sizeof(sequence[0]);i++){
  build(sequence[i],(65533+i)&65535);unsigned steps=0;
  while(runtime.frames==i&&nes_runtime165_step(&runtime))assert(++steps<2048);
  assert(runtime.result==0&&runtime.frames==i+1&&received.state==NES_NATIVE165_IDLE&&read_at==nr);
  assert(retire_calls==i+1&&final_acks==i+1&&!runtime.plan.started&&!runtime.plan.finished&&!runtime.plan.sent);
  assert(!memcmp(&ref,&output,sizeof ref));
 }
 assert(services>wire_calls&&!inside);printf("PASS RUNTIME202 frames=%u bulks=%u transactions=%u services=%u\n",(unsigned)runtime.frames,bulk_count,wire_calls,services);
 for(mode=1;mode<=6;mode++){
  init();build(7,123);unsigned steps=0;while(nes_runtime165_step(&runtime))assert(++steps<2048);
  unsigned expected=mode==2?NES_RUNTIME165_DEADLINE:mode==3?NES_RUNTIME165_SERVICE:mode==6?NES_RUNTIME165_RECEIVE:NES_RUNTIME165_DISPLAY;
  assert(runtime.result==expected&&received.state!=NES_NATIVE165_IDLE&&retire_calls==(mode==4?1u:0u));
  assert(runtime.frames==(mode==4?1u:0u));unsigned before=wire_calls;assert(!nes_runtime165_step(&runtime)&&before==wire_calls);
  printf("PASS RUNTIME202 fault=%u result=%u displayed=%u retire=%u\n",mode,runtime.result,(unsigned)runtime.frames,retire_calls);
 }
 return 0;
}
