/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE_VIDEO165_H
#define NES_NATIVE_VIDEO165_H
#include "nes_native165.h"
/* One caller-owned candidate. Patterns stream to an external staging sink;
 * exact tile/mapping keys are retained only for allocation during this build. */
struct nes_native_video165 {
 /*181 BG allocation keys expire after pattern staging. Reuse that workspace
  * for composed raw CHR and three bounded HDMA tables; no extra frame RAM. */
 union {uint64_t bg_keys[1024];struct {
  uint8_t chr[2048],mode[2][81],enable[81];uint16_t size[3];
 } patch;};uint32_t obj_keys[128];
 uint8_t map[4096],oam[544],cgram[512],hdma[1121];
 uint8_t display_mask; /*178: uniform1e or18, no extra frame buffer. */
 uint16_t hofs[224],vofs[224];
 uint16_t bg_count,obj_count,hdma_size,generation;
 uint8_t groups,objects,error;bool valid;uint8_t patch_count; /*181 tail padding. */
};
/* kind0=BG multiples of16 bytes, kind1=OBJ multiples of32 bytes, <=240.
 * slot is the first contiguous SNES pattern index. The callback must consume
 * bytes synchronously before returning; the pointer expires at return.
 * Sink must stage, never display these tentative writes. False aborts build.
 * Callback execution must be bounded; no automatic retry. */
typedef bool (*nes_native_video165_stage_fn)(void *,unsigned,unsigned,const uint8_t *,unsigned);
/* palette64 is the existing NES->SNES BGR555 lookup. Input must be COMMITTED.
 * Output is tentative until an external upload/display acknowledgement. */
bool nes_native_video165_build(const struct nes_native165 *,const uint16_t palette64[64],struct nes_native_video165 *,nes_native_video165_stage_fn,void *);
#endif
