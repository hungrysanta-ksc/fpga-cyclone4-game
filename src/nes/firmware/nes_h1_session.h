/* SPDX-License-Identifier: MIT */
#ifndef NES_H1_SESSION_H
#define NES_H1_SESSION_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Platform binding still required. SPI: mode0 <=250kHz, byte gap>=1us,
 * SS hold after final rising SCK>=1us; each callback must terminate.
 * reset(true) must assert the actual SNES reset line before FPGA changes.
 * configure must load ONLY the given independent H1 image, report failures,
 * and preserve the existing GBC/menu images. This module never writes SD. */
struct nes_h1_io {
 void *context;
 void (*reset)(void *, bool asserted);
 bool (*configure)(void *, const char *image);
 bool (*transaction)(void *, const uint8_t *tx, uint8_t *rx, size_t n);
 void (*delay_us)(void *, unsigned duration);
};
enum nes_h1_result {
 NES_H1_OK=0, NES_H1_IO_ERROR, NES_H1_ID_ERROR, NES_H1_STATE_ERROR, NES_H1_EPOCH_ERROR
};
enum nes_h1_result nes_h1_start(const struct nes_h1_io *io, uint16_t *epoch);
enum nes_h1_result nes_h1_stop(const struct nes_h1_io *io);
/* stop leaves SNES in reset. Caller must restore menu FPGA/ROM before release.
 * Every start failure also keeps reset asserted; no silent fallback boot. */
#endif
