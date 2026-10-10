/* SPDX-License-Identifier: MIT */
/*140 Read-only first-fault pages. No SD while RUN; STOP still requires reset. */
#include "nes_run136.h"
struct nes_run136_report nes_run136;
static bool observe136(const struct nes_rom_spi_io *io,uint32_t *count) {
 uint8_t tx[8]={0x70,0,0,0,0,0,0,0},rx[8]={0};
 if(!nes_rom_spi_transfer(io,tx,rx))return false;
 nes_run136.observer_id=rx[1];
 if(rx[1]!=0xd7 || (rx[2]&0xfcu) || rx[3]>15)return false;
 nes_run136.flags=rx[2];nes_run136.rom_error=rx[3];
 *count=((uint32_t)rx[4]<<24)|((uint32_t)rx[5]<<16)|((uint32_t)rx[6]<<8)|rx[7];
 return true;
}
static bool context140(const struct nes_rom_spi_io *io) {
 uint8_t tx[8]={0x71,0,0,0,0,0,0,0},hi[8]={0},lo[8]={0};
 if(!nes_rom_spi_transfer(io,tx,hi))return false;
 tx[0]=0x72;
 if(!nes_rom_spi_transfer(io,tx,lo))return false;
 if(hi[1]!=0xd7 || lo[1]!=0xd7 || hi[2]!=1 || lo[2]!=1 ||
    (hi[3]&0x80u) || lo[6]!=nes_run136.rom_error || !lo[6] || lo[7]!=1)return false;
 nes_run136.context_hi=((uint32_t)hi[3]<<24)|((uint32_t)hi[4]<<16)|((uint32_t)hi[5]<<8)|hi[6];
 nes_run136.context_lo=((uint32_t)hi[7]<<24)|((uint32_t)lo[3]<<16)|((uint32_t)lo[4]<<8)|lo[5];
 nes_run136.context_valid=1;
 return true;
}
static bool identify136(const struct nes_rom_spi_io *io,struct nes_menu_probe_report *candidate) {
 struct nes_rom_spi_status s={0};uint32_t count=0;
 nes_run136=(struct nes_run136_report){0};
 if(!sd_query(io,&s)||s.flags||s.count)return false;
 candidate->board_seen=true;candidate->board_id=0x5c;
 return observe136(io,&count)&&nes_run136.flags==1&&!nes_run136.rom_error&&count==0;
}
static bool run136(const struct nes_rom_spi_io *io,uint32_t total,struct nes_mcu_load_report *r) {
 struct nes_rom_spi_status s={0};
 if(!nes_checkpoint112("DISPLAY_NEXT",0,total))return false;
 nes_run136.start_sent=true;
 if(!nes_rom_verified_start(io,total))return nes_cf86_fail094();
 if(!nes_display_enter140())return false;
 for(unsigned i=0;i<200;i++) {
  if(!nes_cf86_check094())return false;
  for(unsigned ms=0;ms<50;ms++){
   wait_us(0,1000);if(!nes_cf86_check094())return false;
  }
  if(!nes_cf86_check094()||!observe136(io,&nes_run136.last))return nes_cf86_fail094();
  if(!i)nes_run136.first=nes_run136.last;
  if(nes_run136.flags||nes_run136.rom_error){
   nes_run136.first_error=1;
   if(nes_run136.rom_error && !context140(io))return nes_cf86_fail094();
   break; /* bounded early return after observed failure, not10s of stale video */
  }
 }
 if(!nes_run136.first_error && (!nes_run136.first||nes_run136.last<=nes_run136.first))nes_run136.first_error=2;
 /* STOP does not clear the observer. A known sticky ROM error must be retained,
  * not treated as a second STOP failure or allowed to overwrite its first cause. */
 uint8_t expected_rom=nes_run136.rom_error;
 uint8_t expected_flags=1u|(expected_rom?2u:0u);
 if(!nes_display_leave140())return false;
 uint8_t stop_tx[8],stop_rx[8];nes_rom_spi_frame(stop_tx,NES_ROM_STOP,total,0);
 if(!nes_rom_spi_transfer(io,stop_tx,stop_rx)||!sd_query(io,&s)||s.flags!=2||s.count!=total)return nes_cf86_fail094();
 r->stop_ok=true;nes_run136.stop_ok=true;
 if(!observe136(io,&nes_run136.stopped))return nes_cf86_fail094();
 if(nes_run136.flags!=expected_flags||nes_run136.rom_error!=expected_rom||nes_run136.stopped<nes_run136.last)nes_run136.stop_error=3;
 uint32_t retained=0;
 if(!observe136(io,&retained))return nes_cf86_fail094();
 if(retained!=nes_run136.stopped||nes_run136.flags!=expected_flags||nes_run136.rom_error!=expected_rom)nes_run136.stop_error=3;
 nes_run136.error=nes_run136.first_error?nes_run136.first_error:nes_run136.stop_error;
 nes_run136.passed=nes_run136.error==0;
 return nes_checkpoint112("DISPLAY_STOPPED",nes_run136.first,nes_run136.stopped);
}
