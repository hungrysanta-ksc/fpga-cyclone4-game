/* SPDX-License-Identifier: MIT */
#ifndef NES_STARTUP222_H
#define NES_STARTUP222_H
#include <stdint.h>
struct nes_startup222 {uint32_t reason,post_reason,signals,ticks;uint8_t reply[20],post_reply[20];};
extern struct nes_startup222 nes_startup222;
enum {NES_STARTUP222_NONE,NES_STARTUP222_READY,NES_STARTUP222_GUARD,
 NES_STARTUP222_IO,NES_STARTUP222_PROTOCOL,NES_STARTUP222_NOT_EMPTY,NES_STARTUP222_NO_RESPONSE};
#endif
