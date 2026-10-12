/* SPDX-License-Identifier: MIT */
#include "nes_native165.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct nes_native165 scene;
struct replay {FILE *file;unsigned calls,mode;bool injected;};
static unsigned byte(const char *s){unsigned v;assert(sscanf(s,"%2x",&v)==1);return v;}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct replay *r=ctx;char a[519],b[519];unsigned count;
 assert(fscanf(r->file,"%u %518s %518s",&count,a,b)==3&&count==n);
 assert(strlen(a)==2*n&&strlen(b)==2*n);r->calls++;
 for(unsigned i=0;i<n;i++){assert(tx[i]==byte(a+2*i));rx[i]=(uint8_t)byte(b+2*i);}
 if(!r->injected&&tx[0]==0xd1&&(r->mode==1||r->mode==2)){r->injected=true;if(r->mode==1)rx[1]^=1;else return false;}
 /* The final POP has happened, but its confirmation is lost: no publish. */
 if(!r->injected&&r->mode==3&&tx[0]==0xd0&&rx[3]==0&&rx[4]==47){r->injected=true;return false;}
 if(!r->injected&&r->mode==4&&tx[0]==0xd3){r->injected=true;return false;}
 return true;
}
static void dump(FILE *f,unsigned kind,unsigned index,uint64_t v){
 /* 96bit record = kind3/gen16/index13/payload64. */
 uint32_t h=(kind<<29)|((uint32_t)scene.generation<<13)|index;
 fprintf(f,"%08x%08x%08x\n",h,(unsigned)(v>>32),(unsigned)v);
}
int main(int argc,char **argv){
 assert(argc==3);assert(sizeof(scene)<=20000);
 for(unsigned mode=0;mode<5;mode++){
  struct replay r={fopen(argv[1],"r"),0,mode,false};assert(r.file);nes_native165_reset(&scene);
  bool ok=true;unsigned loops=0;
  while(ok&&scene.state!=NES_NATIVE165_COMMITTED&&loops++<1000){
   ok=nes_native165_poll(&scene,transfer,&r);
   if(ok&&scene.state==NES_NATIVE165_COMPLETE)ok=nes_native165_prepare(&scene,true,transfer,&r);
  }
  assert(loops<1000);
  if(mode){assert(!ok&&r.injected&&scene.state==NES_NATIVE165_FAILED);}
  else{
   assert(ok&&scene.state==NES_NATIVE165_COMMITTED&&scene.generation==12&&scene.ntiles==15);
   unsigned unused;assert(fscanf(r.file,"%u",&unused)==EOF);FILE *f=fopen(argv[2],"w");assert(f);
   for(unsigned k=0;k<6;k++)for(unsigned i=0;i<scene.counts[k];i++){
    uint64_t v=k==0?scene.maps[i]:k==1?scene.rows[i]:k==2?scene.objects[i]:k==3?scene.exceptions[i]:k==4?scene.raster[i]:scene.palette[i];dump(f,k,i,v);
   }
   for(unsigned i=0;i<scene.ntiles;i++)for(unsigned j=0;j<16;j++)dump(f,6,scene.tiles[i].tag,((uint64_t)scene.tiles[i].kind<<12)|(j<<8)|scene.tiles[i].data[j]);
   fclose(f);nes_native165_consumed(&scene);assert(scene.state==NES_NATIVE165_IDLE);
   printf("PASS RECEIVER165 size=%u records=%u bytes=%u calls=%u\n",(unsigned)sizeof(scene),scene.records,scene.bytes,r.calls);
  }
  fclose(r.file);
 }
 /* Framing and token validation do not depend on a valid scene. */
 uint8_t short_record[3]={0};nes_native165_reset(&scene);assert(!nes_native165_packet(&scene,0,short_record,3));
 nes_native165_reset(&scene);scene.token_valid=true;scene.next_token=1;
 assert(!nes_native165_packet(&scene,2,short_record,3)&&scene.error==18);
 puts("PASS receiver CRC/IO/COMMIT-confirm/PREPARED-IO/truncation/token fail-closed");return 0;
}
