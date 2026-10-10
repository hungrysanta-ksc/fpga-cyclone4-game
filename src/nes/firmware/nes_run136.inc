/* SPDX-License-Identifier: MIT */
/* Included after actual116 guarded transfer/command helpers. No SD while RUN.
 * Counts prove CPU ROM activity only, not CPU correctness or rendered frames. */
#include "nes_run136.h"
struct nes_run136_report nes_run136;
static bool observe136(const struct nes_rom_spi_io *io,uint32_t *count) {
 uint8_t tx[8]={0x70,0,0,0,0,0,0,0},rx[8]={0};
 if(!nes_rom_spi_transfer(io,tx,rx))return false;
 nes_run136.observer_id=rx[1];
 if(rx[1]!=0xd4 || (rx[2]&0xfcu) || rx[3]>15)return false;
 nes_run136.flags=rx[2];nes_run136.rom_error=rx[3];
 *count=((uint32_t)rx[4]<<24)|((uint32_t)rx[5]<<16)|((uint32_t)rx[6]<<8)|rx[7];
 return true;
}
static bool identify136(const struct nes_rom_spi_io *io,struct nes_menu_probe_report *candidate) {
 struct nes_rom_spi_status s={0};uint32_t count=0;
 /* sd_query strictly checks the59 loader identity, errors and length. */
 if(!sd_query(io,&s)||s.flags||s.count)return false;
 candidate->board_seen=true;candidate->board_id=0x59;
 return observe136(io,&count)&&nes_run136.flags==1&&!nes_run136.rom_error&&count==0;
}
static bool run136(const struct nes_rom_spi_io *io,uint32_t total,struct nes_mcu_load_report *r) {
 struct nes_rom_spi_status s={0};
 if(!nes_checkpoint112("RUN_NEXT",0,total))return false;
 nes_run136.start_sent=true; /* Failed reply cannot prove START was not committed. */
 if(!nes_rom_verified_start(io,total))return nes_cf86_fail094();
 /* Sixteen bounded observations; nominal waits16ms, not a physical WCET.
  * Actual116 delay/guard checks remain active. No unbounded count polling. */
 for(unsigned i=0;i<16;i++) {
  if(!nes_cf86_check094())return false;
  wait_us(0,1000);
  if(!nes_cf86_check094()||!observe136(io,&nes_run136.last))return nes_cf86_fail094();
  if(!i)nes_run136.first=nes_run136.last;
  if(nes_run136.flags||nes_run136.rom_error)nes_run136.error=1;
 }
 if(!nes_run136.first||nes_run136.last<=nes_run136.first)nes_run136.error=2;
 /* Normal STOP must be sent even when activity is absent but transport works.
  * Protocol/shared faults instead remain terminal, with no SD recovery. */
 /* RUN->READY STOP retains the image (unlike pre-RUN STOP->IDLE).
  * Require this exact contract, without widening the legacy helper. */
 uint8_t stop_tx[8],stop_rx[8];nes_rom_spi_frame(stop_tx,NES_ROM_STOP,total,0);
 if(!nes_rom_spi_transfer(io,stop_tx,stop_rx)||!sd_query(io,&s)||s.flags!=2||s.count!=total)return nes_cf86_fail094();
 r->stop_ok=true;nes_run136.stop_ok=true;
 if(!observe136(io,&nes_run136.stopped))return nes_cf86_fail094();
 if(nes_run136.flags!=1||nes_run136.rom_error||nes_run136.stopped<nes_run136.last)nes_run136.error=3;
 uint32_t retained=0;
 if(!observe136(io,&retained))return nes_cf86_fail094();
 if(retained!=nes_run136.stopped||nes_run136.flags!=1||nes_run136.rom_error)nes_run136.error=3;
 nes_run136.passed=nes_run136.error==0;
 return nes_checkpoint112("RUN_STOPPED",nes_run136.first,nes_run136.stopped);
}
