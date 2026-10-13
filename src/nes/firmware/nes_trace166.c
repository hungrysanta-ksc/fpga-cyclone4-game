/* SPDX-License-Identifier: MIT */
#include "nes_trace166.h"
struct nes_trace166 nes_trace166;
/* Called ONLY after record validation, inside a CRC-verified packet. Counts
 * received semantic records, not POP retirement or SNES display success. */
void nes_trace166_record(const struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t value){
 struct nes_trace166 *t=&nes_trace166;
 t->records++;t->generation=(uint16_t)gen;t->index=(uint16_t)index;
 t->kind=(uint8_t)kind;t->state=s->state;
 if(s->records>t->max_records)t->max_records=s->records;
 if(kind!=7)return;
 switch(index){
 case 0:if(!t->begins)t->first_begin_tick=t->now;t->begins++;break;
 case 1:t->ends++;break;
 case 2:
  if(!t->aborts){t->first_abort_tick=t->now;t->first_abort_reason=(uint8_t)value;
   t->first_abort_generation=(uint16_t)gen;t->first_abort_records=s->records;t->first_abort_bytes=s->bytes;}
  t->aborts++;t->last_abort_reason=(uint8_t)value;break;
 case 3:t->commits++;break;
 default:break;
 }
}
