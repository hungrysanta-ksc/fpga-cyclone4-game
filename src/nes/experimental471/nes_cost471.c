/* SPDX-License-Identifier: MIT */
#include "nes_cost471.h"
#include <stdio.h>
#include <string.h>
#ifdef NES_COST471_HOST
static uint32_t host_regs471[3];
#define REG471(a) host_regs471[(a)==0xe0001004u?0:(a)==0xe0001000u?1:2]
#else
#define REG471(a) (*(volatile uint32_t *)(uintptr_t)(a))
#endif
struct nes_cost471_bucket nes_cost471_ops[12],nes_cost471_phases[3];
uint32_t nes_cost471_scene_crc;
uint32_t nes_cost471_available,nes_cost471_crc_errors,nes_cost471_transfer_stops;
static uint32_t active,old_trace,old_count;
uint32_t nes_cost471_now(void){return REG471(0xe0001004u);}
void nes_cost471_begin(void){
 memset(nes_cost471_ops,0,sizeof nes_cost471_ops);memset(nes_cost471_phases,0,sizeof nes_cost471_phases);
 nes_cost471_crc_errors=nes_cost471_transfer_stops=0;
 old_trace=REG471(0xe000edfc);old_count=REG471(0xe0001000);
 REG471(0xe000edfc)=old_trace|(1u<<24);REG471(0xe0001000)=old_count|1u;
 uint32_t a=nes_cost471_now();for(volatile unsigned i=0;i<16;i++){}
 nes_cost471_available=nes_cost471_now()!=a;active=1;
}
void nes_cost471_end(void){active=0;REG471(0xe0001000)=old_count;REG471(0xe000edfc)=old_trace;}
static void add(struct nes_cost471_bucket *b,unsigned bytes,uint32_t begin){
 if(!active)return;
 uint32_t d=nes_cost471_now()-begin;
 b->calls++;b->bytes+=bytes;if(nes_cost471_available){b->cycles+=d;if(d>b->max_cycles)b->max_cycles=d;}
}
void nes_cost471_op(unsigned op,unsigned bytes,uint32_t begin){
 unsigned k=op>=0xd0&&op<=0xd3?op-0xd0:op==0xe0?4:op==0xe1?5:op==0xe8?6:op==0xe9?7:op==0xea?8:op==0x70?9:op==0x73?10:11;
 add(&nes_cost471_ops[k],bytes,begin);
}
void nes_cost471_phase(unsigned k,uint32_t begin){if(k<3)add(&nes_cost471_phases[k],0,begin);}
int nes_cost471_append(char *text,unsigned size,int n){
 if(n<0||(unsigned)n>=size)return -1;
 int z=snprintf(text+n,size-(unsigned)n,"cost_schema=471\ncost_clock_hz=84000000\ncost_counter_available=%lu\ncost_scene_crc32_hex=%08lx\ncost_cycles_include_IRQ_guard_and_wait=1\ncost_phase_and_op_are_nested=1\ncost_crc_errors=%lu\ncost_transfer_stops=%lu\ncost_fields=calls,bytes,cycles_hi,cycles_lo,max_cycles\ncost_op_order=D0,D1,D2,D3,E0,E1,E8,E9,EA,70,73,OTHER\n",(unsigned long)nes_cost471_available,(unsigned long)nes_cost471_scene_crc,(unsigned long)nes_cost471_crc_errors,(unsigned long)nes_cost471_transfer_stops);
 if(z<0||(unsigned)z>=size-(unsigned)n)return -1;
 n+=z;
 for(unsigned k=0;k<15;k++){
  const struct nes_cost471_bucket *b=k<12?&nes_cost471_ops[k]:&nes_cost471_phases[k-12];
  z=snprintf(text+n,size-(unsigned)n,"cost_%s_%02u=%lu,%lu,%lu,%lu,%lu\n",k<12?"op":"phase",k<12?k:k-12,(unsigned long)b->calls,(unsigned long)b->bytes,(unsigned long)(b->cycles>>32),(unsigned long)b->cycles,(unsigned long)b->max_cycles);
  if(z<0||(unsigned)z>=size-(unsigned)n)return -1;
 n+=z;
 }
 return n;
}
