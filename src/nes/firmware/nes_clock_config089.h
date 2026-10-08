/* SPDX-License-Identifier: MIT */
#ifndef NES_CLOCK_CONFIG089_H
#define NES_CLOCK_CONFIG089_H
#include <stdbool.h>
#include <stdint.h>
struct clock_image089 {const uint8_t *rle;unsigned size,raw_size;uint32_t crc;};
/* Embedded, trusted CF87 descriptor generated from the pinned087 fit.
 * Caller owns the existing diagnostic scope, RESET and disabled USB IRQ.
 * No SD, scope restart, fault clear, retry, or RESET release. */
bool nes_clock_config089(const struct clock_image089 *);
#endif
