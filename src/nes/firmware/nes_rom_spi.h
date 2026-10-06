/* SPDX-License-Identifier: MIT */
#ifndef NES_ROM_SPI_H
#define NES_ROM_SPI_H
#include <stdbool.h>
#include <stdint.h>
/* Caller owns SPI/GPIO and holds the console reset. Mode0 <=250 kHz.
 * Callbacks perform real pin writes/sample/delay; no hardware setup here. */
struct nes_rom_spi_io {
 void *ctx;
 void (*select)(void *,bool);
 void (*clock)(void *,bool);
 void (*mosi)(void *,bool);
 bool (*miso)(void *);
 void (*wait_us)(void *,unsigned);
};
struct nes_rom_spi_status {uint32_t count;uint8_t flags,protocol_error,loader_error;};
enum {NES_ROM_BEGIN=0x60,NES_ROM_DATA=0x61,NES_ROM_END=0x62,
      NES_ROM_START=0x63,NES_ROM_STOP=0x64,NES_ROM_STATUS=0x65};
void nes_rom_spi_frame(uint8_t out[8],uint8_t command,uint32_t offset,uint8_t arg);
bool nes_rom_spi_transfer(const struct nes_rom_spi_io *,const uint8_t tx[8],uint8_t rx[8]);
bool nes_rom_spi_query(const struct nes_rom_spi_io *,struct nes_rom_spi_status *);
bool nes_rom_spi_command(const struct nes_rom_spi_io *,uint8_t,uint32_t,uint8_t,struct nes_rom_spi_status *);
#endif
