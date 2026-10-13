/* SPDX-License-Identifier: MIT */
/* Included after observe/context/screen helpers by the165 materializer. */
#include "nes_native_runtime165.h"
#include "nes_palette165.inc"
static struct nes_native165 native_receiver165;
/* Logging begins only after native_session165 returns. The plan is dead then;
 * retained error scalars live in native_runtime165, outside this union. */
static union {struct nes_native_video165 video;char log[4096];} native_work165;
char *nes_runtime165_log_buffer(void){return native_work165.log;}
struct nes_native_runtime165 native_runtime165;
static const struct nes_rom_spi_io *native_io165;
static uint32_t native_observed165;
static bool native_first165;
static uint32_t native_ticks165(void *ctx){(void)ctx;return getticks();}
static bool native_transfer165(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)ctx;return nes_native165_bulk(native_io165,tx,rx,n);
}
static bool native_service165(void *ctx){
 (void)ctx;
 if(!nes_cf86_check094())return false;
 uint32_t now=getticks();
 if(!native_first165&&(uint32_t)(now-native_observed165)<5u)return true;
 native_observed165=now;
 if(!observe136(native_io165,&nes_run136.last))return nes_cf86_fail094();
 if(native_first165){nes_run136.first=nes_run136.last;native_first165=false;}
 if(nes_run136.flags||nes_run136.rom_error){
  nes_run136.first_error=1;
  if(nes_run136.rom_error&&!context146(native_io165))return nes_cf86_fail094();
  return false;
 }
 if(!screen146(native_io165))return nes_cf86_fail094();
 return true;
}
static void native_session165(const struct nes_rom_spi_io *io){
 native_io165=io;native_first165=true;native_observed165=getticks();
 (void)nes_runtime165_begin(&native_runtime165,&native_receiver165,&native_work165.video,
  native_palette165,native_transfer165,native_ticks165,native_service165,NULL,6000);
 while(nes_runtime165_step(&native_runtime165)){}
 if(native_runtime165.result!=NES_RUNTIME165_DEADLINE&&!nes_run136.first_error)
  nes_run136.first_error=4;
 if(!native_runtime165.frames&&!nes_run136.first_error)nes_run136.first_error=5;
}
