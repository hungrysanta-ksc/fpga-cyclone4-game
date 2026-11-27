/* SPDX-License-Identifier: MIT */
/* The menu mapper owns PSRAM while the built-in SNES loading screen is live.
 * 0xC00000 (screen program) and 0xFF1000 (text) are outside both game ranges. */
#include "memory.h"
extern int snes_boot_configured;
static __attribute__((noinline,noclone)) bool retail_stage1054(const char *path,struct nes_mcu_load_report *r)
{
 FIL file;
 uint8_t header[16], block[512], interleaved[512];
 const uint32_t total=NES_CART_BYTES;
 uint32_t crc=0xffffffffu;
 bool ok=false;
 r->file_result=f_open(&file,path,FA_READ);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_OPEN;return false;}
 if(!load_read(&file,header,sizeof header,r))goto closed;
 if(nes_image_id(header,f_size(&file))!=nes_board_id){r->result=NES_MCU_LOAD_HEADER;goto closed;}
 crc=load_crc(crc,header,sizeof header);
 snes_boot_configured=0;
 snes_bootprint_center(10,"Loading NES");
 snes_bootprint_center(12,"0%%");
 unsigned shown=0;
 for(uint32_t off=0;off<total;off+=sizeof block){
  if(!load_read(&file,block,sizeof block,r))goto closed;
  crc=load_crc(crc,block,sizeof block);
  uint8_t *data=block;
  uint32_t dest=off;
  if(off>=0x80000){
   dest=0x200000u+(off-0x80000u);
   for(unsigned j=0;j<sizeof block;j++)
    interleaved[(j&~15u)+((j&7u)<<1)+((j>>3)&1u)]=block[j];
   data=interleaved;
  }
  sram_writeblock(data,dest,sizeof block);
  r->acknowledged_bytes=off+sizeof block;
  unsigned pct=(off+sizeof block)*20u/total;
  if(shown!=pct){snes_bootprint_center(12,"%u%%",pct*5u);shown=pct;}
 }
 ok=true;
closed:
 snes_reset(1);
 snes_boot_configured=0;
 r->file_result=f_close(&file);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_CLOSE;return false;}
 if(ok)nes_content_crc=~crc;
 return ok;
}
static __attribute__((noinline)) bool prepare_rom893(const char *path,const char *image,bool chr32,
 struct nes_menu_probe_report *candidate,const struct nes_rom_spi_io *io,bool *changed,bool *begun)
{
 struct nes_mcu_load_report *r=&candidate->sd.load;
 struct nes_rom_spi_status s;
 if(ff3_next_slot){
  /* A retained STOP was already checked against count, identity and flags.
   * This is the same staged image in the same FPGA configuration. */
  candidate->sd.verified=sd_query(io,&s) && s.flags==0x82 && s.count==NES_CART_BYTES;
  return candidate->sd.verified;
 }
 *changed=true;
 if(!nes_diag_fpga_pgm((const uint8_t *)image)||!configured(image) ||
    !nes_return_spi_ready()||!nes_cf86_arm094()||!slow_begin()||!identify136(io,candidate)){
  r->result=NES_MCU_LOAD_CONFIG;return false;
 }
 *begun=true;
 if(!sd_command(io,NES_ROM_BEGIN,0,3,&s)||!sd_command(io,NES_ROM_END,NES_CART_BYTES,0,&s)){
  r->result=NES_MCU_LOAD_SPI;return false;
 }
 r->end_accepted=true;
 candidate->sd.verified=true;
 return true;
}
