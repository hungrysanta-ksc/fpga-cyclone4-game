/* SPDX-License-Identifier: MIT */
#include "nes_native_video165.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 scene;
static struct nes_native_video165 plan;
/* These full pattern arrays model external staging on the HOST only. */
static uint8_t staged_bg[1024][16],staged_obj[128][32];
static unsigned calls,fail_call;
static bool stage(void *ctx,unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 (void)ctx;calls++;if(fail_call&&calls==fail_call)return false;
 assert(kind<2&&slot<(kind?128u:1024u)&&n==(kind?32u:16u));
 memcpy(kind?staged_obj[slot]:staged_bg[slot],b,n);return true;
}
static void write_file(const char *name,const void *p,size_t n){FILE *f=fopen(name,"wb");assert(f&&fwrite(p,1,n,f)==n);fclose(f);}
int main(int argc,char **argv){
 assert(argc==3);FILE *f=fopen(argv[1],"r");assert(f);unsigned hi,mid,lo,token=0;
 const unsigned widths[]={2,1,7,3,7,1,2,8};
 while(fscanf(f,"%8x%8x%8x",&hi,&mid,&lo)==3){
  unsigned kind=hi>>29,gen=(hi>>13)&65535,index=hi&8191;uint64_t v=((uint64_t)mid<<32)|lo;
  uint8_t b[12]={(uint8_t)((kind<<5)|(index>>8)),(uint8_t)index,(uint8_t)(gen>>8),(uint8_t)gen};
  for(unsigned j=0;j<widths[kind];j++)b[4+j]=(uint8_t)(v>>((widths[kind]-1-j)*8));
  assert(nes_native165_packet(&scene,(uint16_t)token++,b,4+widths[kind]));
  /* Transport ACK was tested separately; isolate the committed conversion. */
  if(scene.state==NES_NATIVE165_COMPLETE)scene.state=NES_NATIVE165_PREPARED;
 }
 fclose(f);assert(scene.state==NES_NATIVE165_COMMITTED);
 uint16_t palette[64];f=fopen(argv[2],"rb");assert(f&&fread(palette,2,64,f)==64);fclose(f);
 if(!nes_native_video165_build(&scene,palette,&plan,stage,NULL)){printf("BUILD ERROR %u\n",plan.error);return 1;}
 assert(plan.valid);assert(sizeof(plan)<=16000);write_file("bg.bin",staged_bg,plan.bg_count*16);write_file("obj.bin",staged_obj,plan.obj_count*32);
 write_file("map.bin",plan.map,sizeof(plan.map));write_file("oam.bin",plan.oam,sizeof(plan.oam));write_file("cgram.bin",plan.cgram,sizeof(plan.cgram));write_file("hdma.bin",plan.hdma,plan.hdma_size);
 f=fopen("summary.txt","w");assert(f);fprintf(f,"%u %u %u %u %u %u %u %u\n",(unsigned)sizeof(plan),plan.bg_count,plan.obj_count,plan.groups,plan.objects,plan.hdma_size,plan.hofs[0],plan.vofs[0]);fclose(f);
 unsigned rejects=0;calls=0;fail_call=4;assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL)&&!plan.valid&&calls==4);rejects++;fail_call=0;scene.state=NES_NATIVE165_COMPLETE;assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL)&&!plan.valid);rejects++;scene.state=NES_NATIVE165_COMMITTED;
 uint64_t old=scene.raster[0];scene.raster[0]&=~((uint64_t)255<<36);assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL));rejects++;scene.raster[0]=old;
 unsigned t=0;while(t<scene.ntiles&&scene.tiles[t].tag!=(scene.maps[0]&8191))t++;assert(t<scene.ntiles);
 uint8_t k=scene.tiles[t].kind;scene.tiles[t].kind=0;assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL));rejects++;scene.tiles[t].kind=k;
 if(scene.counts[3]>=2){uint32_t e=scene.exceptions[1];scene.exceptions[1]=scene.exceptions[0];assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL));rejects++;scene.exceptions[1]=e;}
 if(scene.counts[2]>=2){old=scene.objects[1];scene.objects[1]=scene.objects[0];assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL));rejects++;scene.objects[1]=old;}
 assert(nes_native_video165_build(&scene,palette,&plan,stage,NULL));printf("PASS VIDEO165 generation=%u size=%u bg=%u obj=%u groups=%u objects=%u rejects=%u\n",scene.generation,(unsigned)sizeof(plan),plan.bg_count,plan.obj_count,plan.groups,plan.objects,rejects);return 0;
}
