/* SPDX-License-Identifier: MIT */
/*181 Candidate: materialize alongside the paired header as nes_native165.c.
 * Old1741 and new1811 records are intentionally incompatible. */
#include "nes_native165.h"
#include "nes_trace166.h"
#include <string.h>
static const unsigned widths[8]={2,1,7,4,7,1,2,8};
static uint16_t crc16(const uint8_t *p,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*p++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));}return c;}
static uint8_t crc8(const uint8_t *p,unsigned n){uint8_t c=0;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(uint8_t)((c<<1)^((c&128)?7:0));}return c;}
static bool fail(struct nes_native165 *s,unsigned e){s->state=NES_NATIVE165_FAILED;s->error=(uint8_t)e;return false;}
void nes_native165_reset(struct nes_native165 *s){memset(s,0,sizeof(*s));}
static unsigned need(struct nes_native165 *s,unsigned t){return(s->required[t>>2]>>((t&3)*2))&3;}
static void set_need(struct nes_native165 *s,unsigned t,unsigned k){unsigned shift=(t&3)*2;s->required[t>>2]=(uint8_t)((s->required[t>>2]&~(3u<<shift))|(k<<shift));}
static void require_tile(struct nes_native165 *s,unsigned t,unsigned k){unsigned old=need(s,t);if(!old)s->missing++;set_need(s,t,old|k);}
static bool record(struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t v){
 if(kind==7&&index==2){if(s->state!=NES_NATIVE165_IDLE&&gen!=s->generation)return fail(s,1);s->state=NES_NATIVE165_IDLE;return true;}
 if(kind==7&&index==0){
  if(s->state!=NES_NATIVE165_IDLE||(v>>48)!=0x1811||(v&4088))return fail(s,2);
  unsigned g=(unsigned)(v>>42)&63,p=(unsigned)(v>>36)&63,r=(unsigned)(v>>28)&255,o=(unsigned)(v>>20)&255,e=(unsigned)(v>>12)&255;
  if(!g||g>32||!p||p>2||r!=224||o>128||e>128)return fail(s,3);
  uint16_t tok=s->next_token;bool valid=s->token_valid;nes_native165_reset(s);s->next_token=tok;s->token_valid=valid;
  s->counts[0]=(uint16_t)(g*33);s->counts[1]=224;s->counts[2]=(uint16_t)o;s->counts[3]=(uint16_t)e;s->counts[4]=224;s->counts[5]=(uint16_t)(p*32);
  s->generation=(uint16_t)gen;s->patch_count=(uint8_t)(v&7);s->last_tile=65535;s->state=NES_NATIVE165_RECEIVING;return true;
 }
 if(gen!=s->generation)return fail(s,4);
 if(kind==7&&index==3){if(s->state!=NES_NATIVE165_PREPARED||v)return fail(s,5);s->state=NES_NATIVE165_COMMITTED;return true;}
 /* Explicit, irreversible scratch lifetime transition. Counts exclude this
  * control record. No clearing of the bitmap before every need is satisfied. */
 if(kind==7&&index==4){
  if(s->state!=NES_NATIVE165_RECEIVING||s->next_kind==7||v>>32||
     ((v>>16)&65535)!=s->records||(v&65535)!=s->bytes||s->lane||s->missing)return fail(s,29);
  for(unsigned k=0;k<6;k++)if(s->at[k]!=s->counts[k])return fail(s,30);
  unsigned slot=0;
  for(unsigned y=0;y<224;y++)if((s->raster[y]>>49)&1){
   if(((s->raster[y]>>50)&7)!=slot++)return fail(s,31);
  }
  if(slot!=s->patch_count)return fail(s,31);
  s->next_kind=7;s->last_tile=0;return true;
 }
 if(kind==7&&index==1){
  if(s->state!=NES_NATIVE165_RECEIVING||s->next_kind!=7||s->last_tile!=(unsigned)s->patch_count*256||v>>32||((v>>16)&65535)!=s->records||(v&65535)!=s->bytes||s->lane||s->missing)return fail(s,6);
  for(unsigned k=0;k<6;k++)if(s->at[k]!=s->counts[k])return fail(s,7);
  s->state=NES_NATIVE165_COMPLETE;return true;
 }
 if(s->state!=NES_NATIVE165_RECEIVING||kind>6)return fail(s,8);
 if(s->next_kind==7){
  /* Same two-byte kind6 width, now exclusively color6/index11, never CHR. */
  if(kind!=6||index!=s->last_tile||index>=(unsigned)s->patch_count*256||v>>6)return fail(s,32);
  s->raw_pixels[index]=(uint8_t)v;s->last_tile++;s->records++;s->bytes++;return true;
 }
 if(kind<6){
  static const unsigned bits[6]={15,8,49,32,53,6};
  while(s->next_kind<6&&s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;
  if(kind!=s->next_kind||index!=s->at[kind]||(v>>bits[kind]))return fail(s,9);
  switch(kind){
   case 0:s->maps[index]=(uint16_t)v;require_tile(s,(unsigned)v&8191,1);break;
   case 1:if((v>>3)>=s->counts[0]/33u)return fail(s,10);s->rows[index]=(uint8_t)v;break;
   case 2:s->objects[index]=v;require_tile(s,(unsigned)v&8191,2);break;
   case 3:if(((v>>6)&8191)>=7392)return fail(s,11);s->exceptions[index]=(uint32_t)v;require_tile(s,(unsigned)(v>>19),1);break;
   case 4:
    if((v>>49)&1){if((v&((UINT64_C(1)<<49)-1))||((v>>50)&7)>=s->patch_count)return fail(s,12);}
    else if((v>>49)||((v>>44)&31)>=s->counts[5]/32u)return fail(s,12);
    s->raster[index]=v;break;
   case 5:s->palette[index]=(uint8_t)v;break;
  }
  s->at[kind]++;
 }else{
  unsigned lane=(unsigned)(v>>8)&15,k=(unsigned)(v>>12)&3;
  for(unsigned t=0;t<6;t++)if(s->at[t]!=s->counts[t])return fail(s,13);
  if(v>>14||!k||lane!=s->lane)return fail(s,14);
  if(!lane){
   if(s->ntiles==512||(s->last_tile!=65535&&index<=s->last_tile))return fail(s,15);
   if((need(s,index)&k)!=need(s,index))return fail(s,16);
   s->tiles[s->ntiles].tag=(uint16_t)index;s->tiles[s->ntiles].kind=(uint8_t)k;s->last_tile=(uint16_t)index;
  }
  if(index!=s->last_tile||k!=s->tiles[s->ntiles].kind)return fail(s,17);
  s->tiles[s->ntiles].data[lane]=(uint8_t)v;s->lane=(uint8_t)((lane+1)&15);s->bytes++;
  if(lane==15){if(need(s,index)){s->missing--;set_need(s,index,0);}s->ntiles++;}
 }
 s->records++;return true;
}
bool nes_native165_packet(struct nes_native165 *s,uint16_t token,const uint8_t *p,unsigned n){
 if(!s||!p||!n||n>256)return false;
 if(s->state==NES_NATIVE165_FAILED)return false;
 if(s->token_valid&&token!=s->next_token)return fail(s,18);
 for(unsigned pos=0;pos<n;){
  if(n-pos<4)return fail(s,19);
  unsigned tag=((unsigned)p[pos]<<8)|p[pos+1],kind=tag>>13,index=tag&8191,gen=((unsigned)p[pos+2]<<8)|p[pos+3];pos+=4;
  if(n-pos<widths[kind])return fail(s,20);
  uint64_t value=0;for(unsigned j=0;j<widths[kind];j++)value=(value<<8)|p[pos++];
  if(!record(s,kind,gen,index,value))return false;
  nes_trace166_record(s,kind,gen,index,value);
 }
 s->next_token=(uint16_t)(token+1);s->token_valid=true;return true;
}
static void frame(uint8_t *b,uint8_t cmd,uint16_t token,uint8_t arg){b[0]=cmd;b[1]=0;b[2]=(uint8_t)(token>>8);b[3]=(uint8_t)token;b[4]=arg;b[5]=(uint8_t)~arg;b[6]=crc8(b,6);b[7]=0xa5;}
static bool status(uint8_t *r){return r[1]==0xd6&&!(r[2]&0xfc)&&crc8(r+1,6)==r[7];}
bool nes_native165_poll(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx){
 if(!s||!fn||s->state==NES_NATIVE165_FAILED||s->state==NES_NATIVE165_COMMITTED)return false;
 uint8_t tx[259]={0},rx[259];frame(tx,0xd0,0,0);
 if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,21);
 if(!(rx[2]&1))return true;
 uint16_t tok=(uint16_t)((rx[3]<<8)|rx[4]);unsigned n=((unsigned)rx[5]<<8)|rx[6];if(!n||n>256)return fail(s,22);
 memset(tx,0,n+3);tx[0]=0xd1;
 if(!fn(ctx,tx,rx,n+3)||crc16(rx+1,n)!=(uint16_t)((rx[n+1]<<8)|rx[n+2]))return fail(s,23);
 if(!nes_native165_packet(s,tok,rx+1,n))return false;
 frame(tx,0xd2,tok,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,24);
 /* D2 replies before retirement. Confirm it before exposing COMMITTED. */
 frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||
  (uint16_t)((rx[3]<<8)|rx[4])!=(uint16_t)(tok+1))return fail(s,27);
 return true;
}
bool nes_native165_prepare(struct nes_native165 *s,bool accept,nes_native165_transfer_fn fn,void *ctx){
 if(!s||!fn||s->state!=NES_NATIVE165_COMPLETE)return false;
 uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx)||!(rx[2]&2))return fail(s,25);
 frame(tx,0xd3,s->generation,(uint8_t)accept);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,26);
 frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,28);
 s->state=accept?NES_NATIVE165_PREPARED:NES_NATIVE165_FAILED;return true;
}
void nes_native165_consumed(struct nes_native165 *s){if(s&&s->state==NES_NATIVE165_COMMITTED)s->state=NES_NATIVE165_IDLE;}

const uint8_t *nes_native181_pixels(const struct nes_native165 *s,unsigned slot){
 if(!s||s->state!=NES_NATIVE165_COMMITTED||slot>=s->patch_count)return NULL;
 return s->raw_pixels+slot*256;
}
