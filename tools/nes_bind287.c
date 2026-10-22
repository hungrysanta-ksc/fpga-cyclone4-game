/* SPDX-License-Identifier: MIT */
#include <stdint.h>
#include "nes_delta231.h"
extern struct nes_native_video165 video285;
extern uint8_t output285[];
extern unsigned output_size285;
extern const uint8_t *plans267,*material259;
extern unsigned plan_bytes267,plan_at267,plan_sent267,plan_error267,plan_generation267,wait_armed284,plan_cache282;
extern int io259(uint8_t *,unsigned),physical267(uint8_t *,unsigned);
unsigned prefill_active287;
void seed287(unsigned generation){
 plans267=output285;plan_bytes267=plan_at267=plan_sent267=plan_error267=0;
 plan_generation267=generation;wait_armed284=plan_cache282=0;
}
/* Never wait for a consumer while this foreground still owes plan material.
 * A checked E2 is nonblocking; io259 supplies at most two credited banks. */
unsigned prefill287(void){
 uint8_t p[12]={0xe2};plan_bytes267=output_size285;wait_armed284=0;
 prefill_active287=1;unsigned ok=io259(p,12);prefill_active287=0;wait_armed284=0;return ok;
}
unsigned pack287(void){
 /* H2 reads the immutable native fields directly; no flat metadata copy. */
 material259=(const uint8_t *)&video285;
 unsigned n=output_size285;output285[n++]=3;output285[n++]=0;output285[n++]=1;
 output285[n++]=0x83;output285[n++]=plan_generation267;output285[n++]=plan_generation267>>8;
 plan_bytes267=n;return 1;
}
