/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN_SERVICE197_H
#define NES_PLAN_SERVICE197_H
#include "nes_plan191.h"
#include "nes_sink_bulk195.h"
typedef bool (*nes_plan197_transfer)(void *,const uint8_t *,uint8_t *,unsigned);
/* Single MCU owner. transfer returns after SS high and >=2us idle. guard must
 * service deadline/STOP/audio/input outside SPI ownership. No retry on failure.
 * Initialize after common reset, before any E9; sink must already be BUILD.
 * Cancellation is the caller's responsibility on false. One frame per session. */
struct nes_plan197 {
 nes_plan197_transfer transfer;bool (*guard)(void *);void *ctx;struct nes_native_sink165 *sink;
 unsigned poll_limit;uint16_t sent;uint8_t error;bool finished;
};
bool nes_plan197_emit(void *,const struct nes_plan191 *);
bool nes_plan197_finish(struct nes_plan197 *);
#endif
