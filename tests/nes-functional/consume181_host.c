/* SPDX-License-Identifier: MIT */
#include "nes_native_sink165.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct nes_native165 scene;
static struct {uint64_t pre;struct nes_native_video165 p;uint64_t post;} guarded;
#define P guarded.p
static struct nes_native_sink165 sink;
static uint8_t staged[6][16384],old_bg[16384],old_obj[4096];
static unsigned lengths[6],seq,calls,inject,checks;static bool injected;
static uint16_t lut[64];static unsigned rows[7]={0,1,7,8,185,186,223};
static unsigned patches,phase,mask;
extern bool legacy_build(const struct nes_native165 *,const uint16_t *,struct nes_native_video165 *,nes_native_video165_stage_fn,void *);
static unsigned get16(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static bool exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;calls++;assert(n==16+get16(p+12)&&get16(p+2)==seq++&&get16(p+8)==scene.generation);
 if(inject==1&&calls==2){injected=true;return false;}
 if(inject==2&&p[0]==2&&p[1]==5&&get16(p+10)>=1121){injected=true;return false;}
 if(p[0]==1){assert(n==16);memset(lengths,0,sizeof(lengths));memset(staged,0,sizeof(staged));}
 else if(p[0]==2){
  unsigned k=p[1],at=get16(p+10),size=get16(p+12);assert(k<6&&at==lengths[k]&&at+size<=sizeof(staged[k]));
  memcpy(staged[k]+at,p+16,size);lengths[k]+=size;
 }else{
  assert(p[0]==3&&n==40&&get16(p+36)==0x1812&&get16(p+38)==patches);
  for(unsigned k=0;k<6;k++)assert(get16(p+16+k*2)==lengths[k]);
  assert(lengths[5]==(patches?3418:P.hdma_size));
 }
 memset(ack,0,12);ack[0]=p[0]==3?1:0;memcpy(ack+1,p,1);memcpy(ack+2,p+2,8);ack[10]=0x65;ack[11]=0x9a;
 if(inject==3&&p[0]==3){ack[0]=0xe4;injected=true;}
 if(inject==4&&p[0]==3){ack[8]^=1;injected=true;}
 return true;
}
static bool packet(unsigned kind,unsigned index,uint64_t v){
 const unsigned widths[]={2,1,7,4,7,1,2,8};uint8_t b[12];unsigned w=widths[kind],tag=(kind<<13)|index;
 b[0]=(uint8_t)(tag>>8);b[1]=(uint8_t)tag;b[2]=0;b[3]=12;
 for(unsigned j=0;j<w;j++)b[4+j]=(uint8_t)(v>>(8*(w-j-1)));
 return nes_native165_packet(&scene,scene.next_token,b,w+4);
}
static int row_slot(unsigned y){for(unsigned s=0;s<patches;s++)if(rows[s]==y)return (int)s;return -1;}
static unsigned color(unsigned y,unsigned x){return(y*11+x*3+x/7+phase*19)&63;}
static void make_scene(void){
 nes_native165_reset(&scene);
 assert(packet(7,0,(UINT64_C(0x1811)<<48)|(UINT64_C(1)<<42)|(UINT64_C(1)<<36)|(UINT64_C(224)<<28)|(UINT64_C(1)<<20)|patches));
 for(unsigned i=0;i<33;i++)assert(packet(0,i,3));
 for(unsigned y=0;y<224;y++)assert(packet(1,y,y%8));
 assert(packet(2,0,5|(UINT64_C(184)<<13)|(UINT64_C(80)<<22)|(UINT64_C(255)<<38)));
 for(unsigned y=0;y<224;y++){
  int slot=row_slot(y);uint64_t v=slot<0?(uint64_t)mask<<36:(UINT64_C(1)<<49)|((uint64_t)slot<<50);
  assert(packet(4,y,v));
 }
 for(unsigned i=0;i<32;i++)assert(packet(5,i,i==17?0x16:(unsigned[]){15,1,33,48}[i%4]));
 for(unsigned t=0;t<2;t++)for(unsigned i=0;i<16;i++)assert(packet(6,t?5:3,((t?2u:1u)<<12)|(i<<8)|(t?(i<8?255:0):(i<8?0xaa:0xcc))));
 assert(packet(7,4,((uint64_t)scene.records<<16)|scene.bytes));
 for(unsigned s=0;s<patches;s++)for(unsigned x=0;x<256;x++)assert(packet(6,s*256+x,color(rows[s],x)));
 assert(packet(7,1,((uint64_t)scene.records<<16)|scene.bytes));
 /* Receive/prepare transport is separately exercised in wire181. */
 scene.state=NES_NATIVE165_PREPARED;assert(packet(7,3,0));
}
static bool build(void){
 seq=calls=0;injected=false;guarded.pre=guarded.post=UINT64_C(0x181face181face);
 nes_sink165_reset(&sink,exchange,NULL);assert(nes_sink165_begin(&sink,scene.generation));
 bool ok=nes_native_video165_build(&scene,lut,&P,nes_sink165_pattern,&sink);
 assert(guarded.pre==UINT64_C(0x181face181face)&&guarded.post==UINT64_C(0x181face181face));return ok;
}
static bool old_stage(void *ctx,unsigned k,unsigned slot,const uint8_t *b,unsigned n){(void)ctx;memcpy((k?old_obj:old_bg)+slot*(k?32:16),b,n);return true;}
static void dump(const char *name,const void *b,unsigned n){FILE *f=fopen(name,"wb");assert(f&&fwrite(b,1,n,f)==n);fclose(f);}
int main(int argc,char **argv){
 assert(argc==4);patches=(unsigned)atoi(argv[1]);phase=(unsigned)atoi(argv[2]);assert(patches==0||patches==1||patches==7);mask=phase?0x18:0x1e;
 if(phase==2)for(unsigned s=0;s<7;s++)rows[s]=128+s*8;
 FILE *f=fopen(argv[3],"rb");assert(f&&fread(lut,2,64,f)==64);fclose(f);make_scene();assert(build());
 assert(nes_sink165_seal(&sink,&P,5000)&&sink.displayed);
 static const char *names[]={"bg.bin","obj.bin","map.bin","cgram.bin","oam.bin","bundle.bin"};
 for(unsigned k=0;k<6;k++)dump(names[k],staged[k],lengths[k]);
 dump("hdma.bin",P.hdma,P.hdma_size);
 if(patches){dump("raw.bin",P.patch.chr,2048);dump("mode-a.bin",P.patch.mode[0],P.patch.size[0]);dump("mode-b.bin",P.patch.mode[1],P.patch.size[1]);dump("enable.bin",P.patch.enable,P.patch.size[2]);}
 f=fopen("summary.txt","w");assert(f);fprintf(f,"%u %u %u %u %u %u %u %u\n",(unsigned)sizeof(P),P.bg_count,P.obj_count,P.groups,P.objects,P.hdma_size,P.hofs[0],P.vofs[0]);fclose(f);checks++;
 if(!patches){
  static struct nes_native_video165 old;assert(legacy_build(&scene,lut,&old,old_stage,NULL));
  dump("legacy-plan.bin",&old,sizeof(old));dump("candidate-plan.bin",&P,sizeof(P));
  dump("legacy-bg.bin",old_bg,lengths[0]);dump("legacy-obj.bin",old_obj,lengths[1]);
  assert(!memcmp(&old,&P,sizeof(P))&&!memcmp(old_bg,staged[0],lengths[0])&&!memcmp(old_obj,staged[1],lengths[1]));checks++;
 }else{
  uint8_t save=scene.raw_pixels[0];scene.raw_pixels[0]=64;assert(!build()&&P.error==15&&!P.valid);scene.raw_pixels[0]=save;checks++;
  uint64_t r=scene.raster[rows[0]];scene.raster[rows[0]]|=1;assert(!build()&&P.error==15);scene.raster[rows[0]]=r;checks++;
  scene.patch_count--;assert(!build()&&P.error==15);scene.patch_count++;checks++;
 }
 scene.state=NES_NATIVE165_COMPLETE;assert(!build()&&!P.valid);scene.state=NES_NATIVE165_COMMITTED;checks++;
 for(inject=1;inject<=4;inject++){
  if(inject==2&&!patches)continue;
  bool ok=build();if(ok)ok=nes_sink165_seal(&sink,&P,5000);
  assert(!ok&&injected&&!sink.displayed&&sink.state==NES_SINK165_FAULT);
  unsigned previous=calls;assert(!nes_sink165_begin(&sink,13)&&calls==previous);checks++;
 }
 inject=0;assert(build()&&nes_sink165_seal(&sink,&P,5000));checks++;
 printf("PASS CONSUME181 patches=%u phase=%u checks=%u video=%u receiver=%u groups=%u callbacks=%u\n",patches,phase,checks,(unsigned)sizeof(P),(unsigned)sizeof(scene),P.groups,calls);return 0;
}
