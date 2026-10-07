/* SPDX-License-Identifier: MIT */
#ifndef NES_ROM_VERIFY_H
#define NES_ROM_VERIFY_H
#include "nes_rom_spi.h"
enum nes_verify_error {NES_VERIFY_OK,NES_VERIFY_ARGUMENT,NES_VERIFY_IO,NES_VERIFY_PROTOCOL,
 NES_VERIFY_SOURCE,NES_VERIFY_TAG,NES_VERIFY_DATA,NES_VERIFY_TIMEOUT};
struct nes_verify_report {uint32_t compared;enum nes_verify_error error;bool stop_ok;};
/* Source callback supplies one approved payload byte (iNES header excluded).
 * Caller owns GPIO and holds console reset. false requires base/common reset
 * recovery if stop_ok is false. No SD writes or platform reset is performed. */
typedef bool (*nes_verify_source)(void *,uint32_t,uint8_t *);
bool nes_rom_verify(const struct nes_rom_spi_io *,uint32_t,nes_verify_source,void *,struct nes_verify_report *);
bool nes_rom_verified_start(const struct nes_rom_spi_io *,uint32_t);
#endif
