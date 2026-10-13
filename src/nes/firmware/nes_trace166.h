/* SPDX-License-Identifier: MIT */
#ifndef NES_TRACE166_H
#define NES_TRACE166_H
#include "nes_native165.h"
/* Survives per-frame receiver reset and RUN workspace release. No heap/IO. */
struct nes_trace166 {
 uint32_t begins,ends,aborts,commits,records;
 uint32_t now,first_begin_tick,first_abort_tick;
 uint16_t generation,index,first_abort_generation,first_abort_records,first_abort_bytes,max_records;
 uint8_t kind,state,first_abort_reason,last_abort_reason;
};
extern struct nes_trace166 nes_trace166;
void nes_trace166_record(const struct nes_native165 *,unsigned,unsigned,unsigned,uint64_t);
#endif
