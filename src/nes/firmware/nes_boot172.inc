/* SPDX-License-Identifier: MIT */
/* No SD, retry or new buffer. Readiness precedes the first sink BEGIN.
 * 500 ticks = 5s, plus a finite poll cap if ticks stop. Caller restores menu.
 * Stages come from the paired172 client, not legacy display frame counters. */
static bool native_boot172(const struct nes_rom_spi_io *io) __attribute__((noinline));
static bool native_boot172(const struct nes_rom_spi_io *io){
 uint32_t started=getticks();
 for(unsigned polls=0;polls<65536u;polls++){
  if(!native_service165(NULL)||!screen146(io))break;
  if(nes_run136.screen_stage==3)return true;
  if(nes_run136.screen_stage==0xe1||(uint32_t)(getticks()-started)>=500u)break;
 }
 native_runtime165.result=NES_RUNTIME165_SERVICE;
 if(!nes_run136.first_error)nes_run136.first_error=6;
 return false;
}
