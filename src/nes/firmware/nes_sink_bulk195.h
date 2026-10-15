/* SPDX-License-Identifier: MIT */
#ifndef NES_SINK_BULK195_H
#define NES_SINK_BULK195_H
#include "nes_native_sink165.h"
/* Snapshot of194 descriptor6040..604B: ready,kind,length16,offset16,gen16,
 * token32, all little endian. Source must hold the corresponding tile payload
 * until SNES consume (or common cancel). No MCU payload read/copy is required.
 * Uses synchronous exchange/barrier, never enqueue-only completion. Successful
 * return retires a staging chunk; ONLY seal/displayACK retires a whole frame.
 * A failed/ambiguous exchange is terminal; caller must cancel all endpoints.
 * The production descriptor acquisition/plan CDC adapter is not implemented
 * by this function. This API does not poll or acknowledge the FPGA itself. */
bool nes_sink195_bulk(struct nes_native_sink165 *,const uint8_t descriptor[12]);
#endif
