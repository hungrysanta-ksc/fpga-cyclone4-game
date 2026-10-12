/* SPDX-License-Identifier: MIT */
#ifndef NES_NATIVE_SINK165_H
#define NES_NATIVE_SINK165_H
#include "nes_native_video165.h"
/* One immutable mailbox packet, <=256 bytes. Adapter must admit a complete
 * CRC-checked packet and wait for the SNES ACK while servicing fault/STOP/time.
 * A false/ambiguous exchange is terminal until a COMMON transport/client reset.
 * This callback is not a cartridge memory write, nor a direct WRAM address. */
typedef bool (*nes_sink165_exchange_fn)(void *,const uint8_t *,unsigned,uint8_t ack[12]);
enum {NES_SINK165_IDLE,NES_SINK165_BUILD,NES_SINK165_BUSY,NES_SINK165_FAULT};
struct nes_native_sink165 {
 nes_sink165_exchange_fn exchange;void *ctx;
 uint32_t serial;uint16_t generation,sequence,bg_next,obj_next;
 uint8_t state,error;bool displayed;
};
void nes_sink165_reset(struct nes_native_sink165 *,nes_sink165_exchange_fn,void *);
bool nes_sink165_begin(struct nes_native_sink165 *,uint16_t);
bool nes_sink165_pattern(void *,unsigned,unsigned,const uint8_t *,unsigned);
/* Streams tables and waits for actual local compare/upload/ACK. No MCU reads
 * of either candidate, no C delta list. p must stay immutable until return. */
bool nes_sink165_seal(struct nes_native_sink165 *,const struct nes_native_video165 *,uint16_t);
#endif
