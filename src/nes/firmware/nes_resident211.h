/* SPDX-License-Identifier: MIT */
#ifndef NES_RESIDENT211_H
#define NES_RESIDENT211_H
#include "nes_plan191.h"
/* Candidate API, NOT the deployed195 contiguous protocol. A callback writes
 * exactly one arbitrary slot into an INACTIVE destination bank. True means
 * the write completed; commit requires a separate final visible display ACK.
 * Scope is an immutable CHR-ROM content epoch, not a logical mapper bank.
 * Zero slot0 is deliberately emitted each frame: the existing193 collector
 * requires at least one tile before END. This avoids an empty-frame RTL change. */
typedef bool (*nes_resident211_write_fn)(void *,unsigned,const struct nes_plan191 *);
#define NES_RESIDENT211_BITS 144
struct nes_resident211 {
 uint16_t bg[1024]; uint32_t obj[128];
 uint8_t resident[2][NES_RESIDENT211_BITS];
 uint8_t used[NES_RESIDENT211_BITS],dirty[NES_RESIDENT211_BITS];
 uint64_t map_stale[2],map_upload;
 uint32_t epoch,serial,writes,hits;
 uint16_t generation,bg_slots,obj_slots;
 uint8_t active,target; bool displayed,open,prepared,fault;
 nes_resident211_write_fn write; void *ctx;
};
/* Call only after the physical consumer has been reset / old session drained. */
void nes_resident211_reset(struct nes_resident211 *);
bool nes_resident211_begin(struct nes_resident211 *,uint32_t,bool,uint16_t,
                         nes_resident211_write_fn,void *);
/* Same-frame exact keys use the existing video scratch, which may expire
 * during OBJ/raw conversion. Retained keys cover identity BG and masked OBJ;
 * row transformations/cross-tag patterns are regenerated, never guessed. */
unsigned nes_resident211_slot(struct nes_resident211 *,struct nes_native_video165 *,
                             uint64_t,struct nes_plan191 *);
bool nes_resident211_prepare(struct nes_resident211 *,uint64_t);
bool nes_resident211_commit(struct nes_resident211 *,uint32_t,uint16_t,unsigned,bool);
void nes_resident211_abort(struct nes_resident211 *);
bool nes_native_video211_plan(const struct nes_native165 *,const uint16_t [64],
                             struct nes_native_video165 *,struct nes_resident211 *);
#endif
