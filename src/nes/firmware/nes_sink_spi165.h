/* SPDX-License-Identifier: MIT */
#ifndef NES_SINK_SPI165_H
#define NES_SINK_SPI165_H
#include "nes_native_sink165.h"
/* transfer is the existing guarded1..259-byte engine. guard must service/check
 * actual RUN fault, STOP and elapsed deadline; a poll count is not a time unit. */
struct nes_sink_spi165 {
 nes_native165_transfer_fn transfer;void *ctx;
 bool (*guard)(void *);unsigned poll_limit;
};
bool nes_sink_spi165_exchange(void *,const uint8_t *,unsigned,uint8_t ack[12]);
#endif
