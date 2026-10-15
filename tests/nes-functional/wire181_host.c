/* SPDX-License-Identifier: MIT */
#include "nes_native165.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct {unsigned before[4];struct nes_native165 s;unsigned after[4];} guarded;
#define S guarded.s
static unsigned patches,checks;
static void guards(void){for(unsigned i=0;i<4;i++)assert(guarded.before[i]==0xa181face&&guarded.after[i]==0xb181face);}
static void reset(void){for(unsigned i=0;i<4;i++){guarded.before[i]=0xa181face;guarded.after[i]=0xb181face;}nes_native165_reset(&S);}
static unsigned color(unsigned i){return(i*3+(i/256)*11+(i%256)/7)&63;}
static void verify(void){
 guards();assert(S.state==NES_NATIVE165_COMMITTED&&S.generation==12&&S.patch_count==patches&&S.ntiles==3);
 for(unsigned i=0;i<patches*256;i++)assert(nes_native181_pixels(&S,i/256)[i%256]==color(i));
 assert(!nes_native181_pixels(&S,patches));
 for(unsigned i=0;i<3;i++)for(unsigned j=0;j<16;j++)assert(S.tiles[i].data[j]==((S.tiles[i].tag*17+j*5)&255));
}
struct replay {FILE *f;unsigned mode,calls;bool injected,confirm;};
static unsigned hex(const char *s){unsigned v;assert(sscanf(s,"%2x",&v)==1);return v;}
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct replay *r=ctx;char a[519],b[519];unsigned count;
 assert(fscanf(r->f,"%u %518s %518s",&count,a,b)==3&&count==n&&strlen(a)==n*2&&strlen(b)==n*2);r->calls++;
 for(unsigned i=0;i<n;i++){assert(tx[i]==hex(a+i*2));rx[i]=(uint8_t)hex(b+i*2);}
 if(!r->injected&&tx[0]==0xd1&&(r->mode==1||r->mode==2)){r->injected=true;if(r->mode==1)rx[1]^=1;else return false;}
 if(!r->injected&&r->mode==3&&r->confirm&&tx[0]==0xd0){r->injected=true;return false;}
 if(tx[0]==0xd2&&S.state==NES_NATIVE165_COMMITTED)r->confirm=true;
 if(!r->injected&&r->mode==4&&tx[0]==0xd3){r->injected=true;return false;}
 return true;
}
struct rec {unsigned kind,gen,index;uint64_t v;};
static struct rec recs[10000];static unsigned nr;
static bool packet(struct rec r){
 static const unsigned widths[]={2,1,7,4,7,1,2,8};uint8_t b[12];unsigned tag=(r.kind<<13)|r.index,w=widths[r.kind];
 b[0]=(uint8_t)(tag>>8);b[1]=(uint8_t)tag;b[2]=(uint8_t)(r.gen>>8);b[3]=(uint8_t)r.gen;
 for(unsigned j=0;j<w;j++)b[4+j]=(uint8_t)(r.v>>(8*(w-1-j)));
 return nes_native165_packet(&S,S.next_token,b,w+4);
}
static void negatives(void){
 /* Each mutation traverses the actual receiver; no replacement decoder. */
 for(unsigned mode=0;mode<23;mode++){
  reset();bool changed=false,ok=true;unsigned raw=0,chr=0;
  for(unsigned i=0;i<nr&&ok;i++){
   struct rec r=recs[i];bool israw=r.kind==6&&S.next_kind==7;
   if(mode==0&&i==0){r.v=(r.v&UINT64_C(0x0000ffffffffffff))|(UINT64_C(0x1741)<<48);changed=true;}
   if(mode==1&&i==0){r.v|=8;changed=true;}
   if(mode==2&&r.kind==7&&r.index==4){r.v++;changed=true;}
   if(mode==3&&r.kind==7&&r.index==4){changed=true;continue;}
   if(mode==4&&r.kind==7&&r.index==4){ok=packet(r);if(ok)ok=packet(r);changed=true;break;}
   if(mode==5&&r.kind==6&&!israw&&chr++==0){changed=true;continue;}
   if(mode==6&&r.kind==6&&!israw&&r.index==7){changed=true;continue;}
   if(mode==7&&r.kind==4&&r.index==1){r.v|=UINT64_C(1)<<53;changed=true;}
   if(mode==8&&r.kind==4&&r.index==1){r.v=UINT64_C(1)<<50;changed=true;}
   if(mode==9&&r.kind==7&&r.index==1){r.v^=UINT64_C(1)<<16;changed=true;}
   if(mode==10&&r.kind==7&&r.index==1){r.gen++;changed=true;}
   if(mode==11&&r.kind==7&&r.index==3){r.v=1;changed=true;}
   if(mode==12&&r.kind==7&&r.index==3){changed=true;/* skip PREPARED below */}
   if(mode==13&&r.kind==7&&r.index==4){r.index=1;changed=true;}
   if(mode==14&&r.kind==7&&r.index==4){r.v|=UINT64_C(1)<<32;changed=true;}
   if(mode==15&&r.kind==7&&r.index==4){r.index=0;changed=true;}
   if(mode>=16&&patches==0)break;
   if(mode==16&&israw&&raw==0){r.index++;changed=true;}
   if(mode==17&&israw&&raw==1){r.index--;changed=true;}
   if(mode==18&&israw&&raw==0){r.v=64;changed=true;}
   if(mode==19&&israw&&raw==0){r.v=0x1000;changed=true;}
   if(mode==20&&israw&&raw==0){r.gen++;changed=true;}
   if(mode==21&&r.kind==4&&r.index==32){r.v=UINT64_C(1)<<49; r.v|=UINT64_C(7)<<50;changed=true;}
   if(mode==22&&israw&&raw==patches*256-1){changed=true;continue;}
   if(israw)raw++;
   if(r.kind==7&&r.index==3&&mode!=12){assert(S.state==NES_NATIVE165_COMPLETE);S.state=NES_NATIVE165_PREPARED;}
   ok=packet(r);
   if(S.state!=NES_NATIVE165_COMMITTED)assert(!nes_native181_pixels(&S,0));
  }
  if(mode>=16&&patches==0)continue;
  assert(changed&&!ok&&S.state==NES_NATIVE165_FAILED&&!nes_native181_pixels(&S,0));guards();checks++;
 }
 /* ABORT at every phase, then fresh frame; no stale raw pointer. */
 for(unsigned stop=0;stop<nr;stop++){
  if(stop!=0&&recs[stop].kind!=7)continue;
  reset();for(unsigned i=0;i<=stop;i++){
   if(recs[i].kind==7&&recs[i].index==3)S.state=NES_NATIVE165_PREPARED;
   assert(packet(recs[i]));
  }
  assert(packet((struct rec){7,12,2,0}));assert(S.state==NES_NATIVE165_IDLE&&!nes_native181_pixels(&S,0));
  assert(packet(recs[0]));assert(!nes_native181_pixels(&S,0));guards();checks++;
 }
 reset();uint8_t b[3]={0};assert(!nes_native165_packet(&S,0,b,3));checks++;
 reset();S.token_valid=true;S.next_token=1;assert(!nes_native165_packet(&S,2,b,3)&&S.error==18);checks++;
}
int main(int argc,char **argv){
 assert(argc==4);patches=(unsigned)atoi(argv[3]);assert(patches<=7);
 FILE *f=fopen(argv[2],"r");assert(f);unsigned h,hi,lo;
 while(fscanf(f,"%8x%8x%8x",&h,&hi,&lo)==3){assert(nr<10000);recs[nr++]=(struct rec){h>>29,(h>>13)&65535,h&8191,((uint64_t)hi<<32)|lo};}fclose(f);assert(nr);
 for(unsigned mode=0;mode<5;mode++){
  reset();struct replay r={fopen(argv[1],"r"),mode,0,false,false};assert(r.f);bool ok=true;unsigned loops=0;
  while(ok&&S.state!=NES_NATIVE165_COMMITTED&&loops++<2000){
   ok=nes_native165_poll(&S,transfer,&r);
   if(ok&&S.state==NES_NATIVE165_COMPLETE){assert(!nes_native181_pixels(&S,0));ok=nes_native165_prepare(&S,true,transfer,&r);}
  }
  assert(loops<2000);
  if(mode){assert(!ok&&r.injected&&S.state==NES_NATIVE165_FAILED&&!nes_native181_pixels(&S,0));}
  else{assert(ok);verify();unsigned extra;assert(fscanf(r.f,"%u",&extra)==EOF);nes_native165_consumed(&S);assert(!nes_native181_pixels(&S,0));}
  fclose(r.f);guards();checks++;
 }
 negatives();printf("PASS WIRE181 patches=%u pixels=%u checks=%u size=%u\n",patches,patches*256,checks,(unsigned)sizeof(S));return 0;
}
