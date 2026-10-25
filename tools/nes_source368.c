/* SPDX-License-Identifier: MIT */
/* Appended to the checked N5 decoder translation unit. This is executable
 * foreground code; source_io367 is the segmented physical-SPI adapter. IRQ
 * handlers only acknowledge/wake, never take the shared SPI buffer. */
#include "nes_resident211.h"
extern struct nes_resident211 resident285;
extern uint8_t history286[];
extern unsigned block286(const uint8_t *,unsigned,unsigned);
extern void stop286(void),irq_begin284(void),irq_end284(void),wait284(void);
extern uint8_t *source_buffer367(void);
extern int physical267(uint8_t *,unsigned),source_io367(uint8_t *,unsigned,unsigned);

static uint32_t target_tags367[256]; /* Exact 8192-tag membership, not permission. */
unsigned source_token367,source_error367,hint_mode367=1;
volatile unsigned source_cancel367;
unsigned source_blocks367,source_empty367,source_hint_count367,source_hint_tags367;

static unsigned source_crc8_367(const uint8_t *p,unsigned n){
 unsigned c=0;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c&128)?(c<<1)^7:c<<1;c&=255;}return c;
}
static unsigned source_fail367(unsigned code){
 source_error367=code;source_cancel367=1;reset280();stop286();irq_end284();return 0;
}
void source_reset367(void){
 source_token367=source_error367=source_cancel367=0;
 source_blocks367=source_empty367=source_hint_count367=source_hint_tags367=0;
 hint_mode367=1;
}
void source_policy367(unsigned enabled){hint_mode367=enabled!=0;}
static unsigned add_tag367(uint16_t *tags,unsigned n,unsigned tag,unsigned limit){
 if(tag>=8192||n>=limit)return n;
 for(unsigned j=0;j<n;j++)if(tags[j]==tag)return n;
 tags[n++]=(uint16_t)tag;return n;
}
/* Only current CRC-checked geometry records and the last displayed resident
 * context are read. Unused packet lanes repeat a causal tag: the fixed seven
 * entry FPGA cache/EA ABI remains unchanged. A hint never grants DMA/display. */
unsigned source_hint367(void){
 State *s=&receiver280;const struct nes_resident211 *r=&resident285;
 if(!hint_mode367||source_cancel367||s->cold||s->phase==3||s->serial<3||
    !r->displayed||r->open||r->prepared||r->fault||
    r->active>1||r->bg_slots>1024||r->obj_slots>128||r->epoch!=s->epoch||
    r->serial==UINT32_MAX||r->serial+1!=s->serial||(uint16_t)(r->generation+1)!=s->generation)return 0;
 unsigned target=1-r->active;
 if(geometry_groups367){
  for(unsigned j=0;j<256;j++)target_tags367[j]=0;
  for(unsigned i=0;i<r->bg_slots;i++){
   unsigned tag=r->bg[i];if(tag<8192&&(r->resident[target][i/8]&(1u<<(i%8))))target_tags367[tag>>5]|=UINT32_C(1)<<(tag&31);
  }
 }
 uint16_t tags[7];unsigned n=0;
 for(unsigned g=0;g<32&&n<5;g++)if(geometry_groups367&(UINT32_C(1)<<g)){
  for(unsigned i=0;i<33&&n<5;i++){
   unsigned word=u16(history286+66*g+2*i),tag=word&8191;
   if(word&32768)return 0;
   if(!(target_tags367[tag>>5]&(UINT32_C(1)<<(tag&31)))){
    n=add_tag367(tags,n,tag,5);break; /* One causal frontier tag per changed group. */
   }
  }
 }
 /* Complete a small current frontier with causal prior-bank deficits. Scan
  * recent slots first; unchanged tags can still be absent from this bank.
  * Cap at three so old speculative BG/OBJ tails cannot consume this window. */
 if(n&&n<3)for(unsigned i=r->bg_slots;i&&n<3;){
  --i;unsigned tag=r->bg[i];
  if(tag<8192&&(r->used[i/8]&(1u<<(i%8)))&&(r->resident[r->active][i/8]&(1u<<(i%8)))&&
     !(r->resident[target][i/8]&(1u<<(i%8))))n=add_tag367(tags,n,tag,3);
 }
 /* Current changed geometry wins the narrow ROM window. Do not delay these
  * reads with speculative prior-bank/OBJ deficits. Repeated packet lanes hit
  * the same retained seven-entry cache and require no additional ROM bytes. */
 if(!n){
 for(unsigned i=0;i<r->bg_slots&&n<5;i++){
  unsigned tag=r->bg[i];
  if(tag<8192&&(r->used[i/8]&(1u<<(i%8)))&&(r->resident[r->active][i/8]&(1u<<(i%8)))&&!(r->resident[target][i/8]&(1u<<(i%8))))n=add_tag367(tags,n,tag,5);
 }
 if(!n&&!geometry_groups367&&s->phase==1)return 0;
 unsigned obj=0;
 for(unsigned i=0;i<r->obj_slots&&obj<2&&n<7;i++){
  unsigned index=1024+i,key=r->obj[i];
  if(key==UINT32_MAX||!(r->used[index/8]&(1u<<(index%8)))||!(r->resident[r->active][index/8]&(1u<<(index%8)))||
     (r->resident[target][index/8]&(1u<<(index%8))))continue;
  unsigned before=n;n=add_tag367(tags,n,key&8191,7);obj+=n!=before;
 }
 }
 if(!n)return 0;
 source_hint_tags367=n;for(unsigned j=n;j<7;j++)tags[j]=tags[0];
 uint8_t *w=source_buffer367();w[0]=0xea;w[1]=7;w[2]=(uint8_t)s->generation;w[3]=(uint8_t)(s->generation>>8);
 for(unsigned i=0;i<4;i++){w[4+i]=(uint8_t)(s->epoch>>(8*i));w[8+i]=(uint8_t)(s->serial>>(8*i));}
 for(unsigned i=0;i<7;i++){w[12+i*2]=(uint8_t)tags[i];w[13+i*2]=(uint8_t)(tags[i]>>8);}
 uint16_t c=65535;for(unsigned i=0;i<26;i++)c=crc(c,w[i]);w[26]=(uint8_t)c;w[27]=(uint8_t)(c>>8);return 28;
}

unsigned source_receive367(void){
 if(source_cancel367||source_error367)return 0;
 unsigned generation=receiver280.valid?(uint16_t)(receiver280.generation+1):1;
 unsigned pop=0,hinted=0;source_blocks367=source_empty367=source_hint_count367=source_hint_tags367=0;
 irq_end284();
 for(unsigned polls=0;polls<65536;polls++){
  uint8_t *w=source_buffer367();
  for(unsigned j=0;j<13;j++)w[j]=0;
  w[0]=0xd4;w[1]=(uint8_t)(source_token367>>8);w[2]=(uint8_t)source_token367;
  w[3]=(uint8_t)generation;w[4]=(uint8_t)(generation>>8);w[5]=(uint8_t)pop;
  w[6]=(uint8_t)source_crc8_367(w,6);w[7]=0xa5;
  if(!source_io367(w,13,1))return source_fail367(1);
  unsigned flags=w[8],n=w[9],token=((unsigned)w[10]<<8)|w[11];
  if((flags&0xfc)!=0xa8||source_crc8_367(w+8,4)!=w[12]||
     token!=source_token367+pop||n>248||((flags&1)!=0)!=(n!=0)){
   (void)source_io367(w,0,2);return source_fail367(2);
  }
  if(!source_io367(w,n?n+2:0,2))return source_fail367(3);
  source_token367=token;pop=0;
  if(source_cancel367)return source_fail367(4);
  if(!n){source_empty367++;irq_begin284();wait284();continue;}
  geometry_groups367=0;
  if(!block286(w,n,((unsigned)w[n]<<8)|w[n+1])||receiver280.generation!=generation)return source_fail367(5);
  source_blocks367++;
  if(!hinted){
   unsigned bytes=source_hint367();
   if(bytes){if(source_cancel367||!physical267(source_buffer367(),bytes))return source_fail367(6);hinted=1;source_hint_count367++;}
  }
  if(source_token367>=65535)return source_fail367(7);
  if(receiver280.valid&&receiver280.phase==0){
   if(!(flags&2))return source_fail367(8);
   w=source_buffer367();w[0]=0xd5;w[1]=(uint8_t)(token>>8);w[2]=(uint8_t)token;
   w[3]=(uint8_t)generation;w[4]=(uint8_t)(generation>>8);w[5]=3;
   w[6]=(uint8_t)source_crc8_367(w,6);w[7]=0xa5;
   if(source_cancel367||!physical267(w,8))return source_fail367(9);
   source_token367++;irq_end284();return 1;
  }
  pop=1;
 }
 return source_fail367(10);
}
