/* SPDX-License-Identifier: MIT
 * Bounded section/row ingress prototype; selected577 logical checks retained.
 * Canonical CRC covers every expanded value, including inherited rows.
 */
static unsigned get586(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t get32586(const uint8_t *p){return get586(p)|(uint32_t)get586(p+2)<<16;}
static void crc586(struct nes_native165 *s,uint64_t value,unsigned n){
 while(n--){unsigned x=(s->crc586>>8)^(unsigned)(value&255);x^=x>>4;
  s->crc586=(uint16_t)((s->crc586<<8)^(x<<12)^(x<<5)^x);value>>=8;s->length586++;}
}
static bool value586(struct nes_native165 *s,unsigned k,unsigned at,uint64_t value){
 static const uint8_t width[7]={2,1,7,4,7,1,1};
 if(k==6){
  if(s->state!=NES_NATIVE165_RECEIVING||s->next_kind!=7||at!=s->last_tile||
     at>=(unsigned)s->patch_count*256||value>63)return fail(s,40);
  s->raw_pixels[s->last_tile++]=(uint8_t)value;s->bytes++;s->records++;
 }else if(!logical_record(s,k,s->generation,at,value))return false;
 crc586(s,value,width[k]);return true;
}
bool nes_native165_packet(struct nes_native165 *s,uint16_t token,const uint8_t *p,unsigned n){
 if(!s)return false;
 if(s->state==NES_NATIVE165_FAILED)return false;
 if(!p||!n||n>254||(s->token_valid&&token!=s->next_token))return fail(s,18);
 while(n){
  if(n<2)return fail(s,19);
  unsigned tag=get586(p);
  if(tag==0x582){
   if(n<32||p[2]!=1||p[3]>1||p[31]||s->state!=NES_NATIVE165_IDLE)return fail(s,41);
   uint32_t epoch=get32586(p+4),serial=get32586(p+8),base=get32586(p+12);
   bool inherit=p[3]!=0;unsigned old=s->counts[0];
   if(!epoch||serial!=s->serial586+1||!serial||
      (s->epoch586&&epoch!=s->epoch586)||
      (inherit?(!s->base_valid586||base!=s->serial586):base!=0))return fail(s,42);
   unsigned map=get586(p+18),pal=get586(p+28),obj=get586(p+22),exc=get586(p+24);
   if(!map||map>1056||map%33||get586(p+20)!=224||get586(p+26)!=224||
      (pal!=32&&pal!=64)||obj>128||exc>128||p[30]>7)return fail(s,43);
   uint64_t begin=(UINT64_C(0x2233)<<48)|((uint64_t)(map/33)<<42)|((uint64_t)(pal/32)<<36)|
      (UINT64_C(224)<<28)|((uint64_t)obj<<20)|((uint64_t)exc<<12)|p[30];
   if(!logical_record(s,7,get586(p+16),0,begin))return false;
   s->epoch586=epoch;s->serial586=serial;s->base_count586=inherit?(uint16_t)old:0;
   s->inherit586=inherit;s->crc586=65535;s->length586=0;
   p+=32;n-=32;continue;
  }
  if((tag&0xff00)==0xf000){
   if(n<8)return fail(s,44);
   if(tag==0xf003){
    if(get586(p+2)!=s->generation||get32586(p+4)!=s->serial586||
       !logical_record(s,7,s->generation,3,0))return fail(s,45);
    s->base_valid586=true;
   }else{
    if((tag!=0xf004&&tag!=0xf001)||get586(p+2)!=s->length586||
       get586(p+4)!=s->records||get586(p+6)!=s->crc586)return fail(s,46);
    if(!logical_record(s,7,s->generation,tag==0xf004?4:1,
       ((uint64_t)s->records<<16)|s->bytes))return false;
   }
   p+=8;n-=8;continue;
  }
  if(n<6||p[0]>6||s->state!=NES_NATIVE165_RECEIVING)return fail(s,47);
  unsigned k=p[0],mode=p[1],at=get586(p+2),count=get586(p+4);
  unsigned cap=k==6?(unsigned)s->patch_count*256:s->counts[k];
  if(!count||count>256||at!=(k==6?s->last_tile:s->at[k])||at>cap||count>cap-at)return fail(s,48);
  unsigned len=6;
  if(k==0){
   if(count!=33||at%33||(mode!=0&&mode!=3&&mode!=4))return fail(s,49);
   if(mode==0)len+=66;
   else{
    if(!s->inherit586)return fail(s,49);
    unsigned pos=6+(mode==4);if(n<pos+5)return fail(s,49);
    len=pos+5;for(unsigned i=0;i<33;i++)if((p[pos+(i>>3)]>>(i&7))&1)len+=2;
   }
   if(len>n||!nes_row583_apply(s->maps,cap,p,len,s->base_count586))return fail(s,49);
   for(unsigned i=0;i<count;i++)if(!value586(s,0,at+i,s->maps[at+i]))return false;
  }else{
   static const uint8_t widths586[7]={2,1,7,4,7,1,1};unsigned w=widths586[k],pos=6;
   const uint8_t *mask=NULL;
   if(mode==0)len+=count*w;
   else if(mode==1||(mode==2&&k==4))len+=w;
   else if(mode==3&&k==1&&s->inherit586&&count<=32){
    unsigned m=(count+7)/8;if(n<6+m||p[6+m-1]>>(1+(count-1)%8))return fail(s,50);
    mask=p+6;pos+=m;len=pos;
    for(unsigned i=0;i<count;i++)len+=(mask[i>>3]>>(i&7))&1;
   }else return fail(s,50);
   if(len>n)return fail(s,51);
   uint64_t value=0;
   for(unsigned i=0;i<count;i++){
    if(mask&&!((mask[i>>3]>>(i&7))&1))value=s->rows[at+i];
    else if(!mode||mask||!i){value=0;for(unsigned j=0;j<w;j++)value|=(uint64_t)p[pos++]<<(8*j);}
    else if(mode==2)value=raster_next471(value);
    if(!value586(s,k,at+i,value))return false;
   }
  }
  nes_trace166_record(s,k,s->generation,at,mode);
  p+=len;n-=len;
 }
 s->next_token=(uint16_t)(token+1);s->token_valid=true;return true;
}
