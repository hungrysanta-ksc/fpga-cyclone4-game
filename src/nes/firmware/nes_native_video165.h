/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE_VIDEO165_H
#define NES_NATIVE_VIDEO165_H
#include "nes_native165.h"
/* One caller-owned candidate. Patterns stream to an external staging sink;
 * exact tile/mapping keys are retained only for allocation during this build. */
struct nes_native_video165 {
 uint64_t bg_keys[1024];uint32_t obj_keys[128];
 uint8_t map[4096],oam[544],cgram[512],hdma[1121];
 uint16_t hofs[224],vofs[224];
 uint16_t bg_count,obj_count,hdma_size,generation;
 uint8_t groups,objects,error;bool valid;
};
/* kind0=BG16 bytes, kind1=OBJ32 bytes, slot is SNES pattern index.
 * Sink must stage, never display these tentative writes. False aborts build.
 * Callback execution must be bounded; no automatic retry. */
typedef bool (*nes_native_video165_stage_fn)(void *,unsigned,unsigned,const uint8_t *,unsigned);
/* palette64 is the existing NES->SNES BGR555 lookup. Input must be COMMITTED.
 * Output is tentative until an external upload/display acknowledgement. */
bool nes_native_video165_build(const struct nes_native165 *,const uint16_t palette64[64],struct nes_native_video165 *,nes_native_video165_stage_fn,void *);
#endif
