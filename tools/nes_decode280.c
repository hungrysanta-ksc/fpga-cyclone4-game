/* SPDX-License-Identifier: MIT
 * Bounded N5-v2 receiver. Caller owns the 4,910-byte speculative history.
 * Invalidate after STOP, rejected blocks or a failed input commit.
 * A successful input commit retains history for the next source frame.
 * Geometry semantics/renderer are outside this source codec probe.
 */
#include <stdint.h>
static const uint16_t ct[16]={0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,
 0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
static uint16_t crc(uint16_t c,uint8_t b){
 c=(c<<4)^ct[(c>>12)^(b>>4)];return (c<<4)^ct[(c>>12)^(b&15)];
}
static uint16_t u16(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static uint32_t u32(const uint8_t *p){return u16(p)|((uint32_t)u16(p+2)<<16);}
typedef struct {
 uint32_t epoch,serial;
 uint16_t checksum,spans,expanded,generation,raw_count;
 int16_t last;
 uint8_t valid,phase,cold,raw_cold,blocks,raw_blocks,prior_raw;
} State;
State receiver280;
static int reject(void){receiver280.valid=0;receiver280.phase=3;return 0;}
void reset280(void){State *s=&receiver280;s->epoch=0;s->serial=0;s->valid=0;s->phase=0;s->prior_raw=0;}
int feed280(uint8_t *base,const uint8_t *p,unsigned n){
 State *s=&receiver280;
 if(s->phase==3||n>248||!n)return reject();
 while(n){
  unsigned take=0,ci=0;
  if(s->phase==0){
   if(n<20||p[0]!='N'||p[1]!='5'||p[2]!=2||p[3]>3||u16(p+18))return reject();
   uint32_t epoch=u32(p+4),prior=u32(p+8),serial=u32(p+12);
   if(!epoch||!serial||serial==0xffffffffu||prior+1!=serial||
      (s->valid?(epoch!=s->epoch||prior!=s->serial||p[3]&1):
       (serial!=1||prior||p[3]!=3)))return reject();
   s->epoch=epoch;s->serial=serial;s->generation=u16(p+16);
   s->cold=p[3]&1;s->raw_cold=(p[3]>>1)&1;s->valid=0;
   s->checksum=65535;s->spans=0;s->expanded=0;s->blocks=0;s->raw_blocks=0;
   s->last=-1;s->phase=1;take=ci=20;
  }else if(n>=4&&p[0]==255&&p[1]==255&&p[2]==0){
   if(p[3]==3&&s->phase==1){
    if(n<10||u16(p+4)!=s->spans||u16(p+6)!=s->expanded||
       (s->cold&&s->blocks!=68)||base[4397]>2)return reject();
    s->raw_count=(uint16_t)base[4397]*256;
    if(!s->raw_cold&&base[4397]!=s->prior_raw)return reject();
    take=10;ci=8;s->phase=2;s->last=67;
   }else if(p[3]==4&&s->phase==2){
    if(n!=6||(s->raw_cold&&s->raw_blocks!=s->raw_count/64))return reject();
    take=6;ci=4;s->phase=0;s->valid=1;s->prior_raw=base[4397];
   }else return reject();
   for(unsigned i=0;i<ci;i++)s->checksum=crc(s->checksum,p[i]);
   if(s->checksum!=u16(p+ci))return reject();
   p+=take;n-=take;continue;
  }else{
   unsigned index=p[0]&127,at,len;
   if((int)index<=s->last)return reject();
   if(s->phase==1){
    if(index>=68)return reject();
    at=index<32?index*66:2112+(index-32)*64;
    len=index==67?46:index<32?66:64;
    if(s->cold&&index!=s->blocks)return reject();
    s->blocks++;s->spans++;
   }else{
    if(index<68||index>=68u+s->raw_count/64)return reject();
    at=4398+(index-68)*64;len=64;
    if(s->raw_cold&&index!=68u+s->raw_blocks)return reject();
    s->raw_blocks++;
   }
   s->last=index;
   if(p[0]&128){
    if(s->phase!=1||s->cold||index>=32||n<4||(p[1]!=1&&p[1]!=255))return reject();
    if(p[1]==1){for(unsigned i=0;i<64;i++)base[at+i]=base[at+i+2];base[at+64]=p[2];base[at+65]=p[3];}
    else {for(unsigned i=66;i>2;i--)base[at+i-1]=base[at+i-3];base[at]=p[2];base[at+1]=p[3];}
    s->expanded+=66;take=ci=4;
   }else{
    unsigned mb=(len+7)/8,changes=0;
    if(n<1+mb)return reject();
    if(len%8&&(p[mb]>>(len%8)))return reject();
    for(unsigned i=0;i<len;i++)changes+=(p[1+i/8]>>(i%8))&1;
    if(!changes||n<1+mb+changes||((s->phase==1?s->cold:s->raw_cold)&&changes!=len))return reject();
    unsigned j=1+mb;
    for(unsigned i=0;i<len;i++)if(p[1+i/8]&(1<<(i%8))){
     uint8_t value=p[j++];
     if(s->phase==2&&value>=64)return reject();
     base[at+i]=value;
    }
    if(s->phase==1)s->expanded+=changes;
    take=ci=j;
   }
  }
  for(unsigned i=0;i<ci;i++)s->checksum=crc(s->checksum,p[i]);
  p+=take;n-=take;
 }
 return 1;
}
int block280(uint8_t *base,const uint8_t *p,unsigned n,unsigned expected_crc){
 uint16_t c=65535;
 if(n>248||!n)return reject();
 for(unsigned i=0;i<n;i++)c=crc(c,p[i]);
 if(c!=expected_crc)return reject();
 return feed280(base,p,n);
}
int complete280(void){return receiver280.valid&&receiver280.phase==0;}
static uint8_t c8(uint8_t c,uint8_t b){
 c^=b;for(unsigned i=0;i<8;i++)c=c&128?(c<<1)^7:c<<1;return c;
}
int prefix280(uint8_t *p,unsigned token,unsigned generation,unsigned flags){
 if(token>65535||generation>65535||(flags!=0&&flags!=1&&flags!=3))return 0;
 p[0]=flags==3?0xd5:0xd4;p[1]=token>>8;p[2]=token;
 p[3]=generation;p[4]=generation>>8;p[5]=flags;
 uint8_t c=0;for(unsigned i=0;i<6;i++)c=c8(c,p[i]);p[6]=c;p[7]=0xa5;return 1;
}
int reply280(const uint8_t *p,unsigned token){
 uint8_t c=0;for(unsigned i=0;i<4;i++)c=c8(c,p[i]);
 if((p[0]&0xfc)!=0xa8||c!=p[4]||(((unsigned)p[2]<<8)|p[3])!=token||
    (p[0]&1?(!p[1]||p[1]>248):p[1]!=0))return 0;
 return 1;
}
