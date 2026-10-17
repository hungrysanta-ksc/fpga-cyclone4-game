/* SPDX-License-Identifier: MIT */
#ifndef NES_BOOT214_H
#define NES_BOOT214_H
#include <stdint.h>
/* Last SPI status: valid[31:24], read-flags[23:16], error[15:8], stage[7:0].
 * Signals low byte at entry, next byte at exit: RESET asserted/DONE/MCU_RDY.
 * Preserve after runtime begin; never write SD or retry/reset from the gate. */
struct nes_boot214 {uint32_t reason,polls,ticks,first,last,signals;};
extern struct nes_boot214 nes_boot214;
enum {NES_BOOT214_NONE,NES_BOOT214_READY,NES_BOOT214_SERVICE,
 NES_BOOT214_STATUS,NES_BOOT214_COPY,NES_BOOT214_TIMEOUT,NES_BOOT214_POLL_LIMIT};
#endif
