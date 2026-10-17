/* SPDX-License-Identifier: MIT */
#ifndef NES_BUDGET210_H
#define NES_BUDGET210_H
#include "nes_plan191.h"
/* Passive, bounded ROM-session model. Never authorizes a skipped plan/ACK.
 * Bins belong to frame START (5s at the existing10ms clock), not scene labels.
 * A cache hit is exact key equality in a256-entry direct-mapped MODEL only.
 * No source read counter, output-slot protection or SNES timing is inferred. */
enum {B210_FRAMES,B210_RECEIVE,B210_PLAN,B210_SEAL,B210_MAX_GAP,
 B210_INGRESS,B210_E8,B210_E9,B210_E0,B210_E1,B210_OTHER,
 B210_PLANS,B210_OUTPUT,B210_REUSE,B210_REUSE_PLAN,B210_COMPLEX,
 B210_BG,B210_OBJ,B210_MAP_DIRTY,B210_FIELDS};
struct nes_budget210_cache {uint64_t keys[256];uint16_t seen[256];};
struct nes_budget210 {
 struct nes_budget210_cache *cache; /* RUN stack only; revoked before return */
 uint32_t bins[12][B210_FIELDS];
 uint32_t frame_start,last_display,failed_transfers;
 uint16_t serial;uint8_t bin;bool open;
};
extern struct nes_budget210 nes_budget210;
void nes_budget210_reset(void);
void nes_budget210_attach(struct nes_budget210_cache *);
void nes_budget210_detach(void);
void nes_budget210_frame(uint32_t elapsed);
void nes_budget210_wire(unsigned opcode,unsigned n,bool ok);
void nes_budget210_plan(const struct nes_plan191 *);
void nes_budget210_time(unsigned phase,uint32_t ticks);
void nes_budget210_display(uint32_t elapsed,const struct nes_native_video165 *);
int nes_budget210_format(char *,unsigned);
#endif
