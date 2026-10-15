/* SPDX-License-Identifier: MIT */
/* Differential actual converter, plus independently reconstructed map packets.
 * ACKs here are synthetic; actual65816 coverage is a separate coupled test. */
#include "nes_native_sink165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
extern bool legacy_build(const struct nes_native165 *,const uint16_t *,struct nes_native_video165 *,nes_native_video165_stage_fn,void *);
static struct nes_native165 r;
static struct nes_native_video165 p,ref;
static struct nes_native_sink165 sink;
static uint8_t patterns[2][2][16384],previous[4096],candidate[4096];
static unsigned sizes[2][2],map_next,copies,packets,bytes,checks;
static uint16_t lut[64];
static bool stage(void *ctx,unsigned k,unsigned slot,const uint8_t *b,unsigned n){
 unsigned version=*(unsigned *)ctx,at=slot*(k?32:16);
 assert(version<2&&k<2&&at==sizes[version][k]&&at+n<=16384);
 memcpy(patterns[version][k]+at,b,n);sizes[version][k]+=n;return true;
}
static unsigned u16(const uint8_t *b){return b[0]|((unsigned)b[1]<<8);}
static bool exchange(void *ctx,const uint8_t *b,unsigned n,uint8_t ack[12]){
 (void)ctx;assert(n==16+u16(b+12));
 if(b[0]==1)map_next=0;
 if(b[1]==2&&(b[0]==2||b[0]==4||b[0]==5||b[0]==6)){
  unsigned at=u16(b+10),count=b[0]==2?u16(b+12):u16(b+14);
  assert(at==map_next&&at+count<=4096);map_next+=count;packets++;bytes+=n;
  if(b[0]==6){assert(count==64&&n==18&&u16(b+16)==sink.last_generation);memcpy(candidate+at,previous+at,64);copies++;}
  else for(unsigned i=0;i<count;i++)candidate[at+i]=b[16+(b[0]==2?i:i%2)];
 }
 if(b[0]==3){assert(map_next==4096&&u16(b+36)==0x1851);assert(!memcmp(candidate,p.map,4096));memcpy(previous,candidate,4096);}
 memset(ack,0,12);ack[0]=b[0]==3;ack[1]=b[0];memcpy(ack+2,b+2,8);ack[10]=0x65;ack[11]=0x9a;return true;
}
static void scene(unsigned variant){
 memset(&r,0,sizeof(r));r.state=NES_NATIVE165_COMMITTED;r.generation=(uint16_t)(65530+variant);
 r.counts[0]=33;r.counts[1]=224;r.counts[4]=224;r.counts[5]=32;r.ntiles=8;
 for(unsigned i=0;i<8;i++){r.tiles[i].tag=(uint16_t)i;r.tiles[i].kind=1;for(unsigned j=0;j<16;j++)r.tiles[i].data[j]=(uint8_t)(i*31+j*13+variant%2);}
 for(unsigned i=0;i<33;i++)r.maps[i]=(uint16_t)((i%8)|((variant%4)<<13));
 for(unsigned y=0;y<224;y++){r.rows[y]=(uint8_t)(y%8);r.raster[y]=UINT64_C(0x1e)<<36;}
 if(variant%6==2||variant%6==3){r.patch_count=1;r.raster[1]=UINT64_C(1)<<49;for(unsigned x=0;x<256;x++)r.raw_pixels[x]=(uint8_t)((x+variant)&63);}
 for(unsigned i=0;i<32;i++)r.palette[i]=(uint8_t)(i%64);
}
int main(int argc,char **argv){
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*371);
 unsigned zero=0,one=1;memset(&p,0xa5,sizeof(p));nes_sink165_reset(&sink,exchange,NULL);
 for(unsigned v=0;v<30;v++){
  scene(v);uint8_t oldmap[4096];memcpy(oldmap,p.map,4096);unsigned oldgen=p.generation;
  memset(sizes,0,sizeof(sizes));memset(patterns,0,sizeof(patterns));
  assert(legacy_build(&r,lut,&ref,stage,&zero));
  assert(nes_native_video185_build(&r,lut,&p,v!=0,stage,&one));
  uint64_t dirty=v?0:UINT64_MAX;
  if(v)for(unsigned b=0;b<64;b++)if(memcmp(oldmap+b*64,p.map+b*64,64))dirty|=UINT64_C(1)<<b;
  assert(p.map_dirty==dirty&&p.map_inherit==(v!=0)&&p.map_base_generation==(v?oldgen:0));
  ref.map_dirty=p.map_dirty;ref.map_base_generation=p.map_base_generation;ref.map_inherit=p.map_inherit;
  assert(!memcmp(&p,&ref,sizeof(p))&&!memcmp(sizes[0],sizes[1],sizeof(sizes[0]))&&!memcmp(patterns[0],patterns[1],sizeof(patterns[0])));
  assert(nes_sink165_begin(&sink,p.generation));
  for(unsigned k=0;k<2;k++)for(unsigned at=0;at<sizes[1][k];){unsigned n=sizes[1][k]-at;if(n>224)n=224;assert(nes_sink165_pattern(&sink,k,at/(k?32:16),patterns[1][k]+at,n));at+=n;}
  assert(nes_sink165_seal(&sink,&p,5000));checks++;
 }
 /* Deliberately non-repeating maps exercise COPY6 selection and both banks.
  * These are transport fixtures, not evidence of actual game savings. */
 for(unsigned v=0;v<4;v++){
  for(unsigned i=0;i<4096;i++)p.map[i]=(uint8_t)(i*37+(i/19)*7);
  if(v>=2)p.map[78]^=8;
  p.map_dirty=v==0?UINT64_MAX:v==2?UINT64_C(2):0;p.map_inherit=v!=0;p.map_base_generation=sink.last_generation;p.generation++;
  assert(nes_sink165_begin(&sink,p.generation));sink.bg_next=p.bg_count;sink.obj_next=p.obj_count;
  unsigned before=copies;assert(nes_sink165_seal(&sink,&p,5000));assert(v==0?copies==before:copies>before);checks++;
 }
 p.map_base_generation=sink.last_generation^1;p.generation++;assert(nes_sink165_begin(&sink,p.generation));sink.bg_next=p.bg_count;sink.obj_next=p.obj_count;
 unsigned before=packets;assert(!nes_sink165_seal(&sink,&p,5000)&&sink.error==5&&packets==before);checks++;
 r.state=NES_NATIVE165_COMPLETE;assert(!nes_native_video185_build(&r,lut,&p,true,stage,&one)&&!p.valid);checks++;
 assert(!nes_native_video185_build(&r,lut,&p,true,stage,&one)&&p.error==17);checks++;
 printf("PASS MAP185 checks=%u copies=%u map_packets=%u map_wire=%u video=%u sink=%u\n",checks,copies,packets,bytes,(unsigned)sizeof(p),(unsigned)sizeof(sink));
 nes_sink165_reset(&sink,exchange,NULL);p=ref;
 for(int f=1;f<argc;f++){
  FILE *in=fopen(argv[f],"rb");assert(in&&fread(p.map,1,4096,in)==4096&&fgetc(in)==EOF);fclose(in);
  p.map_dirty=0;p.map_inherit=f>1;p.map_base_generation=sink.last_generation;p.generation=(uint16_t)f;
  unsigned dirty=0;for(unsigned b=0;b<64;b++)if(memcmp(previous+b*64,p.map+b*64,64)){p.map_dirty|=UINT64_C(1)<<b;dirty++;}
  unsigned oldcopies=copies,oldpackets=packets,oldbytes=bytes;
  assert(nes_sink165_begin(&sink,p.generation));sink.bg_next=p.bg_count;sink.obj_next=p.obj_count;
  assert(nes_sink165_seal(&sink,&p,5000));
  printf("MAPFILE index=%d dirty=%u copies=%u packets=%u wire=%u\n",f,dirty,copies-oldcopies,packets-oldpackets,bytes-oldbytes);
 }
 return 0;
}
