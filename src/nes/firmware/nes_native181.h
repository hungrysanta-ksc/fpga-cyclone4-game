/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE165_H
#define NES_NATIVE165_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
struct nes_native165_tile {uint16_t tag;uint8_t kind,data[16];};
/* Caller-owned bounded storage; no heap or full pixel frame. */
struct nes_native165 {
 uint16_t maps[1056];uint8_t rows[224],palette[64];
 uint64_t objects[128],raster[224];uint32_t exceptions[128];
 struct nes_native165_tile tiles[512];
 /*181 Required CHR bitmap becomes raw pixels ONLY after CHR_END validation.
  * Keep the API/type for runtime integration; materialize as nes_native165.h. */
 union {uint8_t required[2048];uint8_t raw_pixels[2048];};
 uint16_t generation,counts[6],at[6],records,bytes,ntiles,missing,last_tile;
 uint8_t state,next_kind,lane,error,patch_count;
 bool token_valid;uint16_t next_token;
};
enum {NES_NATIVE165_IDLE,NES_NATIVE165_RECEIVING,NES_NATIVE165_COMPLETE,NES_NATIVE165_PREPARED,NES_NATIVE165_COMMITTED,NES_NATIVE165_FAILED};
typedef bool (*nes_native165_transfer_fn)(void *,const uint8_t *,uint8_t *,unsigned);
void nes_native165_reset(struct nes_native165 *);
bool nes_native165_packet(struct nes_native165 *,uint16_t,const uint8_t *,unsigned);
/* One bounded STATUS + optional READ/POP. No automatic retry after I/O failure. */
bool nes_native165_poll(struct nes_native165 *,nes_native165_transfer_fn,void *);
bool nes_native165_prepare(struct nes_native165 *,bool,nes_native165_transfer_fn,void *);
/* COMMITTED data must be consumed before caller permits another BEGIN. */
void nes_native165_consumed(struct nes_native165 *);
/* No tentative pixels: pointer is valid only until consumed/reset/ABORT. */
const uint8_t *nes_native181_pixels(const struct nes_native165 *,unsigned);
#endif
