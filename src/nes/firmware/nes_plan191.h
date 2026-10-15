/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN191_H
#define NES_PLAN191_H
#include "nes_native_video165.h"
/* Streamed one tile at a time. Native bytes never appear in this plan.
 * alt[y] replaces low plane's source tag only; 0xffff means base tag. */
struct nes_plan191 {uint16_t generation,slot,tag;uint8_t kind,mask,row[16];uint16_t alt[8];};
typedef bool (*nes_plan191_fn)(void *,const struct nes_plan191 *);
bool nes_native_video191_plan(const struct nes_native165 *,const uint16_t *,
 struct nes_native_video165 *,bool,nes_plan191_fn,void *);
#endif
