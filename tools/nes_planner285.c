/* SPDX-License-Identifier: MIT
 * Diagnostic harness for the unchanged planner. Buffers below are probe
 * storage, not new target allocations or a physical SPI/ACK implementation.
 */
#include "nes_delta231.h"
#include "nes_plan_wire199.h"
#include <string.h>
#include "order247.h"
struct nes_native165 input285;
struct nes_native_video165 video285;
struct nes_resident211 resident285;
struct nes_dirty231 dirty285;
uint16_t palette285[64];
uint8_t output285[8192],batch285[240];
unsigned output_size285,batch_size285,batch_count285,calls285,error285;
extern void trace259(unsigned,unsigned);
void *memset(void *p,int v,size_t n){unsigned char *q=p;while(n--)*q++=(unsigned char)v;return p;}
void *memcpy(void *p,const void *s,size_t n){unsigned char *q=p;const unsigned char *r=s;while(n--)*q++=*r++;return p;}
void *memmove(void *p,const void *s,size_t n){unsigned char *q=p;const unsigned char *r=s;if(q<r)while(n--)*q++=*r++;else while(n){n--;q[n]=r[n];}return p;}
int memcmp(const void *a,const void *b,size_t n){const unsigned char *p=a,*q=b;while(n--){if(*p!=*q)return *p-*q;p++;q++;}return 0;}
static bool flush285(void){
 if(!batch_count285)return true;
 if(output_size285+batch_size285+3>sizeof output285)return false;
 output285[output_size285++]=batch_size285;output285[output_size285++]=batch_size285>>8;output285[output_size285++]=batch_count285;
 memcpy(output285+output_size285,batch285,batch_size285);output_size285+=batch_size285;
 trace259(2,batch_count285);batch_size285=batch_count285=0;return true;
}
static bool emit285(void *ctx,unsigned bank,const struct nes_plan191 *q){
 (void)ctx;if(bank!=resident285.target)return false;
 uint8_t b[32];unsigned n=nes_plan199_encode(q,b);if(!n)return false;
 calls285++;trace259(1,q->kind);
 if(batch_count285==15||batch_size285+n>240)if(!flush285())return false;
 order247_insert(batch285,batch_size285,b,n);batch_size285+=n;batch_count285++;
 return batch_count285<15||flush285();
}
void reset285(void){nes_resident211_reset(&resident285);nes_dirty231_reset(&dirty285);memset(&video285,0,sizeof video285);}
/* Recorded canonical receiver packets, unrelated to timing of the N5 wire. */
unsigned load285(const uint8_t *p,unsigned n){
 nes_native165_reset(&input285);unsigned tok=0;
 while(n){unsigned len=*p++;n--;if(len>n)return 0;
  if(p[0]==0xe0&&p[1]==3){if(input285.state!=NES_NATIVE165_COMPLETE)return 0;input285.state=NES_NATIVE165_PREPARED;}
  if(!nes_native165_packet(&input285,tok++,p,len))return 0;p+=len;n-=len;
 }
 return input285.state==NES_NATIVE165_COMMITTED;
}
unsigned begin285(void){
 output_size285=batch_size285=batch_count285=calls285=error285=0;
 return nes_resident211_begin(&resident285,1,true,input285.generation,emit285,0);
}
unsigned plan285(unsigned state){
 input285.state=state;
 unsigned ok=nes_native_video231_plan(&input285,palette285,&video285,&resident285,&dirty285);
 error285=video285.error;return ok&&flush285();
}
unsigned commit285(void){
 return nes_dirty231_commit(&dirty285,resident285.serial,resident285.generation,resident285.target,true)&&
 nes_resident211_commit(&resident285,resident285.serial,resident285.generation,resident285.target,true);
}
unsigned layout285(unsigned index){
 switch(index){
 case 0:return offsetof(struct nes_native_video165,map);
 case 1:return offsetof(struct nes_native_video165,cgram);
 case 2:return offsetof(struct nes_native_video165,oam);
 case 3:return sizeof(struct nes_native165);
 case 4:return sizeof(struct nes_native_video165);
 case 5:return sizeof(struct nes_resident211);
 case 6:return sizeof(struct nes_dirty231);
 default:return 0;
 }
}
