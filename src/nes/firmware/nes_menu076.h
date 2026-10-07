/* SPDX-License-Identifier: MIT */
#ifndef NES_MENU076_H
#define NES_MENU076_H
#include <stdbool.h>
#include <stdint.h>
#include "smc.h"
#define NES_MENU076_SIZE 65536u
#define NES_MENU076_CRC 0xc014b571u
uint32_t nes_menu_crc076(uint32_t crc,const uint8_t *data,unsigned size);
bool nes_menu_classify076(snes_romprops_t *props);
bool nes_menu_approved076(const snes_romprops_t *props);
#endif
