/* SPDX-License-Identifier: MIT */
#ifndef NES_SD_READBACK_H
#define NES_SD_READBACK_H
#include "nes_mcu_loader.h"
#include "nes_rom_verify.h"
struct nes_sd_readback_report {
 struct nes_mcu_load_report load;
 struct nes_verify_report verify;
 bool verified;
};
/* Synchronous internal diagnostic only; no menu entry or installable image.
 * image must be approved044+059, NOT stock044 or056 protocol54.
 * Always holds console reset; never STARTs. true means safe to reload menu,
 * including recovered test failures. Check load.result and verified separately.
 * false requires fail-closed recovery, keeping RESET/USB protection held. */
bool nes_sd_readback_probe(const char *,const char *,struct nes_sd_readback_report *);
#endif
