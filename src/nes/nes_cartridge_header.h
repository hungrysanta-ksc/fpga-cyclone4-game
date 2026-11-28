/* SPDX-License-Identifier: MIT */
#ifndef NES_CARTRIDGE_HEADER_H
#define NES_CARTRIDGE_HEADER_H
#include <stdint.h>
#include <string.h>

enum nes_container { NES_UNKNOWN, NES_INES, NES_20, NES_UNIF, NES_FDS };
struct nes_cartridge {
 uint32_t prg_size, chr_size, prg_offset, chr_offset, tail_size;
 uint16_t mapper;
 uint8_t submapper, wiring, console, timing, device, console_detail, misc;
 /* NES 2.0 encodes volatile/nonvolatile sizes as two nibbles per byte.
  * In legacy iNES, work_ram is the original count in 8 KiB units. */
 uint8_t work_ram, pattern_ram, diskdude;
 enum nes_container format;
};

static inline int nes_rom_size(uint8_t low, unsigned high, unsigned shift, uint32_t *out) {
 if(high != 15) {
  *out = ((high << 8) | low) << shift;
  return 1;
 }
 unsigned exponent = low >> 2, multiplier = (low & 3u) * 2 + 1;
 if(exponent >= 32 || multiplier > (UINT32_MAX >> exponent)) return 0;
 *out = (uint32_t)multiplier << exponent;
 return 1;
}

/* size is the size reported by FatFS, including the header. */
static inline int nes_decode_cart(const uint8_t h[16], uint32_t size, struct nes_cartridge *c) {
 *c = (struct nes_cartridge){0};
 if(size < 16) return 0;
 if(!memcmp(h,"UNIF",4)) { c->format=NES_UNIF; return 0; }
 if(!memcmp(h,"FDS\032",4)) { c->format=NES_FDS; return 0; }
 if(memcmp(h,"NES\032",4)) return 0;
 unsigned extended = (h[7] & 12) == 8;
 c->format = extended ? NES_20 : NES_INES;
 c->diskdude = !extended && !memcmp(h+7,"DiskDude!",9);
 unsigned flags7 = c->diskdude ? 0 : h[7];
 c->mapper = (flags7 & 0xf0) | (h[6] >> 4);
 c->wiring = h[6] & 15;
 c->console = flags7 & 3;
 if(extended) {
  c->mapper |= (h[8] & 15) << 8;
  c->submapper = h[8] >> 4;
  c->work_ram=h[10]; c->pattern_ram=h[11]; c->timing=h[12]&3;
  c->console_detail=h[13]; c->misc=h[14]&3; c->device=h[15]&63;
  if((h[12]&0xfc) || (h[14]&0xfc) || (h[15]&0xc0)) return 0;
 } else if(!c->diskdude) {
  c->work_ram=h[8]; c->timing=h[9]&1;
  if(flags7 & 12) return 0;
  for(unsigned i=10;i<16;i++) if(h[i]) return 0;
  if(h[9]&0xfe) return 0;
 }
 unsigned sizes = extended ? h[9] : 0;
 if(!nes_rom_size(h[4],sizes&15,14,&c->prg_size) ||
    !nes_rom_size(h[5],sizes>>4,13,&c->chr_size) || !c->prg_size) return 0;
 c->prg_offset = 16 + ((c->wiring & 4) ? 512 : 0);
 if(size < c->prg_offset || c->prg_size > size-c->prg_offset) return 0;
 c->chr_offset = c->prg_offset + c->prg_size;
 if(c->chr_size > size-c->chr_offset) return 0;
 c->tail_size = size-c->chr_offset-c->chr_size;
 return !c->misc || c->tail_size != 0;
}

/* Only select layouts the installed board image and both loaders can consume.
 * Legacy horizontal CNROM and MMC5 retain the loader's full-file CRC gate. */
static inline unsigned nes_cart_profile(const struct nes_cartridge *c) {
 if(c->console || c->timing || c->console_detail || c->device>1 || c->misc ||
    c->tail_size || (c->wiring&12)) return 0;
 if(c->format==NES_20) {
  if(c->mapper==5 && !c->submapper && c->wiring==2 && c->prg_size==1048576 &&
     !c->chr_size && c->work_ram==0x70 && c->pattern_ram==7) return 0x84;
  if(c->submapper!=1 || c->work_ram) return 0;
  if(c->mapper==3 && c->wiring==1 && c->prg_size==32768 && c->chr_size==32768 && !c->pattern_ram) return 0x81;
  if(c->mapper==7 && !c->wiring && c->prg_size==524288 && !c->chr_size && c->pattern_ram==7) return 0x82;
 } else if(c->format==NES_INES && c->work_ram<=1) {
  if(c->mapper==4 && !(c->wiring&~2u) && c->prg_size==524288) {
   if(c->chr_size==262144) return 0x7c;
   if(!c->chr_size) return 0x7d;
  }
  if(c->mapper==3 && c->wiring<=1 && c->prg_size==32768 && c->chr_size==32768) return 0x81;
  if(c->mapper==7 && !c->wiring && c->prg_size==524288 && !c->chr_size) return 0x82;
  if(c->mapper==21 && !c->wiring && c->prg_size==262144 && c->chr_size==131072) return 0x83;
 }
 return 0;
}
#endif
