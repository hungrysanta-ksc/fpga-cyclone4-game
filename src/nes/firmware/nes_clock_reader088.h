/* SPDX-License-Identifier: MIT */
#ifndef NES_CLOCK_READER088_H
#define NES_CLOCK_READER088_H
#include <stdbool.h>
#include <stdint.h>
enum clock_result088 {CLOCK088_PENDING,CLOCK088_ACTIVE,CLOCK088_ABSENT,
 CLOCK088_UNSTABLE,CLOCK088_NO_PROGRESS,CLOCK088_IO_ERROR,CLOCK088_PROTOCOL_ERROR};
struct clock_report088 {
 enum clock_result088 result;
 uint32_t started,elapsed,attempts,frames;
 uint8_t initial[16],sample[2][16];
 unsigned captured;
};
/* Caller has configured CF87, owns RESET/USB and the shared diagnostic scope.
 * True = observation collected (including absent/unstable/no-progress), NOT
 * hardware approval. False = shared fault; no later SD/SRAM/configuration IO.
 * Does not configure FPGA, enable logging, reset a fault or release RESET. */
bool nes_clock_collect088(struct clock_report088 *);
#endif
