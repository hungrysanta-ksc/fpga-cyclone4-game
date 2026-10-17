/* SPDX-License-Identifier: MIT */
#ifndef NES_PLAN215_H
#define NES_PLAN215_H
#include <stdint.h>
/* First invalid E8 only. No successful-poll copy, retry, or extra SPI. */
enum nes_plan215_phase {NES_PLAN215_FLUSH=1,NES_PLAN215_FINISH=2,NES_PLAN215_RETIRE=3,NES_PLAN215_REARM=4};
enum nes_plan215_reason {NES_PLAN215_HEADER=1,NES_PLAN215_RESERVED=2,NES_PLAN215_CRC=3,
 NES_PLAN215_FLAGS=4,NES_PLAN215_COUNT=5,NES_PLAN215_DESCRIPTOR=6,NES_PLAN215_EMPTY=7,
 NES_PLAN215_EARLY_END=8,NES_PLAN215_RETIRE_STATE=9,NES_PLAN215_REARM_STATE=10};
struct nes_plan215 {uint16_t sent,generation,bytes;uint8_t count,phase,reason,valid;uint8_t reply[20];};
extern struct nes_plan215 nes_plan215;
#endif
