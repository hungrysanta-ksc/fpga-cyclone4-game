/* SPDX-License-Identifier: MIT
 * Experimental591: ARM row decision, one bitmap request, independent CRC16.
 * Nonmap577 semantics remain. No cached digest or second map allocation.
 */
static unsigned get591(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t get32591(const uint8_t *p){return get591(p)|(uint32_t)get591(p+2)<<16;}
static void put591(uint8_t *p,uint32_t v,unsigned n){while(n--){*p++=(uint8_t)v;v>>=8;}}
static uint32_t digest591(const uint16_t *row,unsigned mode,unsigned edge){
 uint32_t c=0xffffffff;
 for(unsigned i=0;i<33;i++){
  unsigned v=mode==1?(i==32?edge:row[i+1]):mode==2?(i?row[i-1]:edge):row[i];
  c=crc32_update(c,(uint8_t)v);c=crc32_update(c,(uint8_t)(v>>8));
 }
 return c^0xffffffff;
}
static bool begin591(struct nes_native165 *s,const uint8_t *p){
 unsigned count=get591(p+18),pal=get591(p+28),obj=get591(p+22),exc=get591(p+24);
 uint32_t serial=get32591(p+8),base=get32591(p+12);
 if(get591(p)!=0x591||p[2]!=1||p[3]>1||p[31]||s->state!=NES_NATIVE165_IDLE||
    !s->r_hello||get32591(p+4)!=s->r_epoch||!serial||serial!=s->r_serial+1||
    (p[3]?(!s->r_base||base!=s->r_serial):base!=0)||
    !count||count>1056||count%33||get591(p+20)!=224||get591(p+26)!=224||
    (pal!=32&&pal!=64)||obj>128||exc>128||p[30]>7)return fail(s,41);
 uint16_t token=s->next_token;bool have=s->token_valid;
 /* Preserve maps and the prefix history; clear all current semantics/required. */
 memset(s->rows,0,sizeof(*s)-offsetof(struct nes_native165,rows));
 s->next_token=token;s->token_valid=have;
 s->counts[0]=(uint16_t)count;s->counts[1]=224;s->counts[2]=(uint16_t)obj;
 s->counts[3]=(uint16_t)exc;s->counts[4]=224;s->counts[5]=(uint16_t)pal;
 s->generation=(uint16_t)get591(p+16);s->patch_count=p[30];s->last_tile=65535;
 s->state=NES_NATIVE165_RECEIVING;s->r_active=serial;s->r_cold=!p[3];
 s->r_request=p[3]?0:(count==1056?0xffffffff:(1u<<(count/33))-1);
 s->r_seen=0;s->r_row=0;s->r_repair=false;s->r_base=false;
 s->r_crc=65535;s->r_length=0;return true;
}
static bool summaries591(struct nes_native165 *s,const uint8_t *p,unsigned n){
 if(!s->r_ord){if(n<32||!begin591(s,p))return false;p+=32;n-=32;}
 if(s->state!=NES_NATIVE165_RECEIVING)return fail(s,42);
 unsigned rows=s->counts[0]/33;
 while(!s->r_cold&&s->r_row<rows&&n>=8){
  unsigned at=s->r_row*33,first=get591(p+4),last=get591(p+6),mode=0;
  uint16_t *row=s->maps+at;uint32_t want=get32591(p);
  if(first>32767||last>32767)return fail(s,43);
  if(at+33>s->r_base_count)mode=3;
  else if(digest591(row,0,0)!=want){
   if(digest591(row,1,last)==want)mode=1;
   else if(digest591(row,2,first)==want)mode=2;
   else mode=3;
  }
  if(mode==1){memmove(row,row+1,64);row[32]=(uint16_t)last;}
  else if(mode==2){memmove(row+1,row,64);row[0]=(uint16_t)first;}
  else if(mode==3)s->r_request|=1u<<s->r_row;
  s->r_row++;p+=8;n-=8;
 }
 if(n){
  if(n!=8||(!s->r_cold&&s->r_row!=rows)||get591(p)!=0x5900||get591(p+2)!=rows||get591(p+6)!=s->generation)return fail(s,44);
  s->r_mapcrc=(uint16_t)get591(p+4);s->r_phase=1;s->r_ord=255;s->r_pending=!s->r_cold;
 }
 return true;
}
static bool rows591(struct nes_native165 *s,const uint8_t *p,unsigned n){
 if(s->r_pending||s->state!=NES_NATIVE165_RECEIVING)return fail(s,45);
 while(n>8){
  if(n<72||p[0]||p[1]||get591(p+4)!=33)return fail(s,46);
  unsigned at=get591(p+2),row=at/33;
  if(at%33||at+33>s->counts[0]||!(s->r_request&(1u<<row))||(s->r_seen&(1u<<row)))return fail(s,47);
  for(unsigned i=0;i<33;i++){
   unsigned v=get591(p+6+2*i);if(v>32767)return fail(s,48);s->maps[at+i]=(uint16_t)v;
  }
  s->r_seen|=1u<<row;p+=72;n-=72;
 }
 if(n){
  if(n!=8||get591(p)!=0x5901||get591(p+2)!=(unsigned)__builtin_popcount(s->r_request)||
     get591(p+4)!=s->r_mapcrc||get591(p+6)!=s->generation||s->r_seen!=s->r_request)return fail(s,49);
  if(crc16((const uint8_t *)s->maps,2*s->counts[0])!=s->r_mapcrc){
   if(s->r_repair)return fail(s,50);
   s->r_repair=true;s->r_seen=0;s->r_request=s->counts[0]==1056?0xffffffff:(1u<<(s->counts[0]/33))-1;
   s->r_pending=true;s->r_ord=255;return true;
  }
  /* No tentative row changes required-tag ownership before independent CRC. */
  for(unsigned i=0;i<s->counts[0];i++)if(!logical_record(s,0,s->generation,i,s->maps[i]))return false;
  /* Source must hold after row-END: D2 alone cannot distinguish ACCEPT from
   * REPAIR. Explicit ACCEPT prevents nonmap from sealing ahead of a repair. */
  s->r_phase=2;s->r_ord=255;s->r_pending=true;s->r_request=0;
 }
 return true;
}
bool nes_native165_packet(struct nes_native165 *s,uint16_t token,const uint8_t *p,unsigned n){
 if(!s||!p||n<2||n>254)return false;
 if(s->state==NES_NATIVE165_FAILED)return false;
 if((s->token_valid&&token!=s->next_token)||p[0]!=s->r_phase||p[1]!=s->r_ord)return fail(s,18);
 unsigned phase=*p;p+=2;n-=2;
 if(phase==0){if(!summaries591(s,p,n))return false;s->r_token=token;}
 else if(phase==1){if(!rows591(s,p,n))return false;s->r_token=token;}
 else if(phase==4){
  if(n!=8||get591(p)!=0xf003||get591(p+2)!=s->generation||get32591(p+4)!=s->r_active||
     !logical_record(s,7,s->generation,3,0))return fail(s,51);
  s->r_commit=true;
 }else if(phase==2||phase==3){
  while(n){
   if(n==8&&get591(p)==(phase==2?0xf004:0xf001)){
    if(get591(p+2)!=s->r_length||get591(p+4)!=s->records||get591(p+6)!=s->r_crc||
       !logical_record(s,7,s->generation,phase==2?4:1,((uint64_t)s->records<<16)|s->bytes))return fail(s,52);
    s->r_phase++;s->r_ord=255;n=0;
   }else{
    if(n<4)return fail(s,19);
    unsigned tag=((unsigned)p[0]<<8)|p[1],kind=tag>>13,index=tag&8191,gen=((unsigned)p[2]<<8)|p[3];
    if(kind==0||kind==6||(kind==7&&index<0x800)||
       ((phase==3)!=(kind==7&&index>=0x1000&&index<0x1700)))return fail(s,53);
    unsigned width=widths[kind];if(n<4+width)return fail(s,20);
    uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[4+j];
    if(!record(s,kind,gen,index,value))return false;
    nes_trace166_record(s,kind,gen,index,value);p+=4+width;n-=4+width;
   }
  }
 }else return fail(s,54);
 s->r_ord++;s->next_token=(uint16_t)(token+1);s->token_valid=true;return true;
}

static bool request591(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx,bool hello){
 uint8_t tx[24]={0xd4,1},rx[24];
 put591(tx+2,s->r_epoch,4);put591(tx+6,hello?s->r_serial+1:s->r_active,4);
 put591(tx+10,hello?0:s->generation,2);put591(tx+12,hello?0:s->r_token,2);
 put591(tx+14,hello?0:s->r_request,4);
 tx[18]=hello?(s->r_base?1:0):(s->r_phase==2?4:s->r_repair?3:2);
 put591(tx+20,crc16(tx,20),2);tx[22]=0x5a;tx[23]=0xa5;
 if(!fn(ctx,tx,rx,24))return fail(s,55);
 frame(tx,0xd0,0,0);
 if(!fn(ctx,tx,rx,8)||!status(rx)||!!(rx[2]&4)==!!s->r_toggle)return fail(s,56);
 s->r_toggle^=1;s->r_pending=false;
 if(hello)s->r_hello=true;
 return true;
}
