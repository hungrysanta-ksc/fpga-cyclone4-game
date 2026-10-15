/* SPDX-License-Identifier: MIT */
#include "nes_plan191.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_native165 r,poison;
static struct nes_native_video165 ref,candidate,again;
static uint8_t bg[16384],obj[4096];static unsigned sizes[2];
static struct nes_plan191 plans[1200];static unsigned count,repeat_at;
static uint16_t lut[64];static FILE *list,*expected;
static bool stage(void *ctx,unsigned kind,unsigned slot,const uint8_t *data,unsigned n){
 (void)ctx;unsigned at=slot*(kind?32:16);assert(kind<2&&at==sizes[kind]);
 assert(at+n<=(kind?sizeof obj:sizeof bg));memcpy((kind?obj:bg)+at,data,n);sizes[kind]+=n;return true;
}
static bool plan(void *ctx,const struct nes_plan191 *q){
 if(ctx){assert(repeat_at<count&&!memcmp(q,&plans[repeat_at++],sizeof *q));return true;}
 assert(count<1200);plans[count++]=*q;
 fprintf(list,"%u %u %u %u %u",q->kind,q->generation,q->slot,q->tag,q->mask);
 for(unsigned i=0;i<16;i++)fprintf(list," %u",q->row[i]);
 for(unsigned i=0;i<8;i++)fprintf(list," %u",q->alt[i]);
 fprintf(list,"\n");
 unsigned kind=q->kind==1,n=kind?32:16,at=q->slot*n;assert(at+n<=sizes[kind]);
 for(unsigned i=0;i<n;i++)fprintf(expected,"%02x\n",(kind?obj:bg)[at+i]);
 return true;
}
static void scene(unsigned variant){
 memset(&r,0,sizeof r);r.state=NES_NATIVE165_COMMITTED;r.generation=(uint16_t)(100+variant);
 r.counts[0]=33;r.counts[1]=224;r.counts[4]=224;r.counts[5]=variant>=5?64:32;r.ntiles=10;
 for(unsigned t=0;t<10;t++){r.tiles[t].tag=(uint16_t)t;r.tiles[t].kind=3;for(unsigned b=0;b<16;b++)r.tiles[t].data[b]=(uint8_t)(t*31+b*13+variant);}
 for(unsigned x=0;x<33;x++)r.maps[x]=(uint16_t)((x%8)|((x%4)<<13));
 for(unsigned y=0;y<224;y++){
  r.rows[y]=(uint8_t)(y%8);
  r.raster[y]=(UINT64_C(0x1e)<<36)|((uint64_t)(variant%8)<<30);
  if(variant>=5&&y>=112)r.raster[y]|=UINT64_C(1)<<44;
 }
 if(variant>=1){r.counts[3]=3;
  r.exceptions[0]=(9u<<19)|((18*33+2)<<6)|(2<<3)|3;
  r.exceptions[1]=(2u<<19)|((19*33+2)<<6)|(3<<3)|4;
  r.exceptions[2]=(8u<<19)|((20*33+2)<<6)|(4<<3)|6;
 }
 if(variant>=2){r.counts[2]=2;
  r.objects[0]=2|(UINT64_C(108)<<13)|(UINT64_C(20)<<22)|(UINT64_C(0xff)<<38);
  r.objects[1]=4|(UINT64_C(108)<<13)|(UINT64_C(60)<<22)|(UINT64_C(0xc1)<<30)|(UINT64_C(0x7e)<<38)|(UINT64_C(1)<<46);
 }
 if(variant>=3){r.patch_count=variant==3?1:7;
  for(unsigned i=0;i<r.patch_count;i++){
   r.raster[31+i*32]=(UINT64_C(1)<<49)|((uint64_t)i<<50);
   for(unsigned x=0;x<256;x++)r.raw_pixels[i*256+x]=(uint8_t)((x+i*11)&63);
  }
 }
 for(unsigned i=0;i<r.counts[5];i++)r.palette[i]=(uint8_t)(i%32);
}
int main(void){
 for(unsigned i=0;i<64;i++)lut[i]=(uint16_t)(i*371);
 unsigned total=0;
 for(unsigned v=0;v<8;v++){
  scene(v);memset(sizes,0,sizeof sizes);count=repeat_at=0;
  assert(nes_native_video185_build(&r,lut,&ref,false,stage,NULL));
  char name[64];sprintf(name,"scene%u.plans",v);list=fopen(name,"w");assert(list);
  sprintf(name,"scene%u.expected",v);expected=fopen(name,"w");assert(expected);
  assert(nes_native_video191_plan(&r,lut,&candidate,false,plan,NULL));
  assert(!memcmp(&ref,&candidate,sizeof ref));fclose(list);fclose(expected);
  poison=r;for(unsigned t=0;t<poison.ntiles;t++)memset(poison.tiles[t].data,0xa5,16);
  assert(nes_native_video191_plan(&poison,lut,&again,false,plan,&poison));
  assert(repeat_at==count&&!memcmp(&candidate,&again,sizeof candidate));
  sprintf(name,"scene%u.mem",v);FILE *f=fopen(name,"w");assert(f);
  for(unsigned t=0;t<r.ntiles;t++)for(unsigned b=0;b<16;b++)fprintf(f,"%02x\n",r.tiles[t].data[b]);
  fclose(f);
  printf("SCENE %u plans=%u bg=%u obj=%u raw=%u\n",v,count,sizes[0],sizes[1],r.patch_count);total+=count;
 }
 printf("PASS PLAN191 scenes=8 plans=%u metadata=%u plan_struct=%u\n",total,(unsigned)sizeof ref,(unsigned)sizeof(struct nes_plan191));
 return 0;
}
