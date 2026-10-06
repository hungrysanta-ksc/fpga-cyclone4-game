/* SPDX-License-Identifier: MIT */
#ifndef NES_H1_STM32_H
#define NES_H1_STM32_H
#include <stdbool.h>
#include <stdint.h>
bool nes_h1_is_marker(const uint8_t *path);
/* Blocking diagnostic until physical RESET or H1 fault.
 * Returns true only after base FPGA restoration; SNES remains held in reset.
 * Caller reloads menu. False must fail closed, never release SNES. */
bool nes_h1_run(void);
#endif
