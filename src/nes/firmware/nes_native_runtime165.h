/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE_RUNTIME165_H
#define NES_NATIVE_RUNTIME165_H
#include "nes_sink_spi165.h"
enum { NES_RUNTIME165_RUNNING, NES_RUNTIME165_DEADLINE, NES_RUNTIME165_SERVICE,
 NES_RUNTIME165_IO, NES_RUNTIME165_RECEIVE, NES_RUNTIME165_DISPLAY,
 NES_RUNTIME165_LIMIT, NES_RUNTIME165_ARGUMENT };
/* Caller-owned buffers, one session after COMMON producer/sink/client reset.
 * ticks is monotonic modulo32; limit <2^31 ticks. service runs only between
 * complete SPI transactions, never recursively from inside the SPI engine.
 * The caller owns STOP, reset, logging and menu recovery after any terminal.
 */
struct nes_native_runtime165 {
 struct nes_native165 *receiver;struct nes_native_video165 *video;
 const uint16_t *palette;
 nes_native165_transfer_fn transfer;uint32_t (*ticks)(void *);
 bool (*service)(void *);void *ctx;
 struct nes_sink_spi165 transport;struct nes_native_sink165 sink;
 uint32_t started,limit,steps,frames,transactions,wire_bytes;
 uint16_t generation;uint8_t result,receiver_error,video_error;bool inside_transfer;
};
bool nes_runtime165_begin(struct nes_native_runtime165 *,struct nes_native165 *,
 struct nes_native_video165 *,const uint16_t palette[64],
 nes_native165_transfer_fn,uint32_t (*ticks)(void *),bool (*service)(void *),
 void *,uint32_t limit_ticks);
/* One bounded receiver poll or one synchronous frame conversion/upload.
 * All packet/ACK waits still call the time/fault service guard. */
bool nes_runtime165_step(struct nes_native_runtime165 *);
#endif
