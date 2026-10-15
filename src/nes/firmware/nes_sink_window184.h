/* SPDX-License-Identifier: MIT */
#ifndef NES_SINK_WINDOW184_H
#define NES_SINK_WINDOW184_H
#include <stdbool.h>
#include <stdint.h>
typedef bool (*nes_window184_transfer)(void *,const uint8_t *,uint8_t *,unsigned);
/* RUN-owned. Only common-reset initialization; never retry an ambiguous write.
 * Data enqueue success means copied to transport, NOT SNES/display completion.
 * No packet pointers survive a callback. The endpoint validates EVERY SNES ACK.
 */
struct nes_sink_window184 {
 nes_window184_transfer transfer;bool (*guard)(void *);void *ctx;
 unsigned poll_limit;uint16_t sent,retired;uint8_t last[10],error;
 bool initialized,ever_sent;
 /* Last CRC/identity-valid status only; counters above are MCU observations. */
 uint8_t status_flags,ack_status;
};
bool nes_window184_init(struct nes_sink_window184 *,nes_window184_transfer,bool (*)(void *),void *,unsigned);
bool nes_window184_enqueue(void *,const uint8_t *,unsigned);
bool nes_window184_barrier(void *,const uint8_t *,unsigned,uint8_t ack[12]);
bool nes_window184_drain(struct nes_sink_window184 *,uint8_t ack[12]);
#endif
