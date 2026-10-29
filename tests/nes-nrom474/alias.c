/* SPDX-License-Identifier: MIT */
#include "nes_cost471.h"
#include <assert.h>
#include <stdio.h>
struct nes_rom_spi_io;
bool nes_native165_bulk(const struct nes_rom_spi_io *,const uint8_t *,uint8_t *,unsigned);
bool nes_game149_transfer(const struct nes_rom_spi_io *,const uint8_t *,uint8_t *);
int main(void){
 uint8_t b[20]={0xe1},tx[20]={0xe0},rx[20];nes_cost471_begin();
 assert(nes_native165_bulk(NULL,b,b,20));b[0]=0xe9;assert(nes_native165_bulk(NULL,b,b,14));
 assert(nes_native165_bulk(NULL,tx,rx,20));b[0]=0x70;assert(nes_game149_transfer(NULL,b,b));
 assert(nes_cost471_ops[5].calls==1&&nes_cost471_ops[7].calls==1&&nes_cost471_ops[4].calls==1&&nes_cost471_ops[9].calls==1&&nes_cost471_ops[11].calls==0);
 nes_cost471_end();puts("PASS474 actual wrapper opcode snapshot: in-place E1/E9/70 and separate E0");return 0;
}
