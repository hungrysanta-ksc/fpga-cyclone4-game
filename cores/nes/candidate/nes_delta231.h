/* SPDX-License-Identifier: MIT */
#ifndef NES_DELTA231_H
#define NES_DELTA231_H
#include "nes_resident211.h"
/* Candidate only: transport CRC/token verification and source epoch admission
 * are prerequisites. No new frame storage; no production wire binding yet. */
struct nes_source231 {
 uint32_t epoch,serial,pending;
 uint16_t generation,next,end,spans,bytes,want_spans,want_bytes,raw_at;
 bool valid,open,full,geometry,fault;
};
bool nes_source231_begin(struct nes_source231 *,struct nes_native165 *,uint32_t,uint32_t,uint32_t,uint16_t,bool,unsigned,unsigned);
bool nes_source231_write(struct nes_source231 *,struct nes_native165 *,unsigned,unsigned,const uint8_t *,unsigned);
bool nes_source231_raster(struct nes_source231 *,struct nes_native165 *,unsigned,unsigned,unsigned,uint64_t);
bool nes_source231_shift(struct nes_source231 *,struct nes_native165 *,unsigned,unsigned,int,uint16_t);
bool nes_source231_geometry(struct nes_source231 *,struct nes_native165 *);
bool nes_source231_raw(struct nes_source231 *,struct nes_native165 *,unsigned,const uint8_t *,unsigned);
bool nes_source231_end(struct nes_source231 *,struct nes_native165 *);
/* Clear only after common STOP/reset; incomplete updates poison the base. */
void nes_source231_reset(struct nes_source231 *);

#define NES_DIRTY231_BYTES 54
struct nes_dirty231 {
 uint8_t stale[2][NES_DIRTY231_BYTES];
 uint32_t epoch,serial;
 uint16_t generation;
 uint8_t target;bool valid,open,prepared,fault,raw;
};
void nes_dirty231_reset(struct nes_dirty231 *);
bool nes_dirty231_begin(struct nes_dirty231 *,const struct nes_resident211 *);
bool nes_dirty231_material(struct nes_dirty231 *,const struct nes_native165 *,const uint16_t *,const struct nes_native_video165 *);
void nes_dirty231_map(struct nes_dirty231 *,unsigned);
bool nes_dirty231_commit(struct nes_dirty231 *,uint32_t,uint16_t,unsigned,bool);
void nes_dirty231_abort(struct nes_dirty231 *);
uint8_t nes_dirty231_byte(const struct nes_native_video165 *,unsigned,unsigned);
bool nes_native_video231_plan(const struct nes_native165 *,const uint16_t [64],struct nes_native_video165 *,struct nes_resident211 *,struct nes_dirty231 *);
#endif
