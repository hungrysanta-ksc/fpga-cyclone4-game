/* sd2snes - SD card based universal cartridge for the SNES
Copyright (C) 2009-2010 Maximilian Rehkopf <otakon@gmx.net>
AVR firmware portion

Inspired by and based on code from sd2iec, written by Ingo Korb et al.
See sdcard.c|h, config.h.

FAT file system access based on code by ChaN, Jim Brain, Ingo Korb,
see ff.c|h.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; version 2 of the License only.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

memory.c: RAM operations
*/


#include "config.h"
#include "gbc_log_policy.h"
#include "uart.h"
#include "fpga.h"
#include "cfg.h"
#include "cic.h"
#include "crc.h"
#include "crc32.h"
#include "ff.h"
#include "fileops.h"
#include "spi.h"
#include "fpga_spi.h"
#include "led.h"
#include "smc.h"
#include "memory.h"
#include "snes.h"
#include "timer.h"
#include "rle.h"
#include "diskio.h"
#include "snesboot.h"
#include "msu1.h"
#include "cli.h"
#include "cheat.h"
#include "rtc.h"
#include "savestate.h"
#include "sgb.h"
#ifdef GBC_SAVE_G12
#include "gbc_save.h"
#include "gbc_menu.h"
#endif
#ifdef GBC_DUMP_G12
#include "gbc_dump.h"
#endif

#include <string.h>
char* hex = "0123456789ABCDEF";

extern snes_romprops_t romprops;
extern uint32_t saveram_crc_old, saveram_crc, saveram_offset;
extern sgb_romprops_t sgb_romprops;
extern uint32_t saveram_crc_old;
extern uint8_t sram_crc_valid;
extern uint8_t sram_crc_init;
extern uint32_t sram_crc_romsize;
extern cfg_t CFG;
extern snes_status_t STS;

void sram_hexdump(uint32_t addr, uint32_t len) {
  static uint8_t buf[16];
  uint32_t ptr;
  for(ptr=0; ptr < len; ptr += 16) {
    sram_readblock((void*)buf, ptr+addr, 16);
    uart_trace(buf-ptr-addr, ptr+addr, 16);
  }
}

void sram_writebyte(uint8_t val, uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98); /* WRITE */
  FPGA_TX_BYTE(val);
  FPGA_WAIT_RDY();
  FPGA_DESELECT();
}

uint8_t sram_readbyte(uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88); /* READ */
  FPGA_WAIT_RDY();
  uint8_t val = FPGA_RX_BYTE();
  FPGA_DESELECT();
  return val;
}

void sram_writeshort(uint16_t val, uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98); /* WRITE */
  FPGA_TX_BYTE(val&0xff);
  FPGA_WAIT_RDY();
  FPGA_TX_BYTE((val>>8)&0xff);
  FPGA_WAIT_RDY();
  FPGA_DESELECT();
}

void sram_writelong(uint32_t val, uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98); /* WRITE */
  FPGA_TX_BYTE(val&0xff);
  FPGA_WAIT_RDY();
  FPGA_TX_BYTE((val>>8)&0xff);
  FPGA_WAIT_RDY();
  FPGA_TX_BYTE((val>>16)&0xff);
  FPGA_WAIT_RDY();
  FPGA_TX_BYTE((val>>24)&0xff);
  FPGA_WAIT_RDY();
  FPGA_DESELECT();
}

uint16_t sram_readshort(uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88);
  FPGA_WAIT_RDY();
  uint32_t val = FPGA_RX_BYTE();
  FPGA_WAIT_RDY();
  val |= ((uint32_t)FPGA_RX_BYTE()<<8);
  FPGA_DESELECT();
  return val;
}

uint32_t sram_readlong(uint32_t addr) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88);
  FPGA_WAIT_RDY();
  uint32_t val = FPGA_RX_BYTE();
  FPGA_WAIT_RDY();
  val |= ((uint32_t)FPGA_RX_BYTE()<<8);
  FPGA_WAIT_RDY();
  val |= ((uint32_t)FPGA_RX_BYTE()<<16);
  FPGA_WAIT_RDY();
  val |= ((uint32_t)FPGA_RX_BYTE()<<24);
  FPGA_DESELECT();
  return val;
}

void sram_readlongblock(uint32_t* buf, uint32_t addr, uint16_t count) {
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88);
  uint16_t i=0;
  while(i<count) {
    FPGA_WAIT_RDY();
    uint32_t val = (uint32_t)FPGA_RX_BYTE()<<24;
    FPGA_WAIT_RDY();
    val |= ((uint32_t)FPGA_RX_BYTE()<<16);
    FPGA_WAIT_RDY();
    val |= ((uint32_t)FPGA_RX_BYTE()<<8);
    FPGA_WAIT_RDY();
    val |= FPGA_RX_BYTE();
    buf[i++] = val;
  }
  FPGA_DESELECT();
}

uint16_t sram_readblock(void* buf, uint32_t addr, uint16_t size) {
  uint16_t count=size;
  uint8_t* tgt = buf;
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88);   /* READ */
  while(count--) {
    FPGA_WAIT_RDY();
    *(tgt++) = FPGA_RX_BYTE();
  }
  FPGA_DESELECT();
  return size;
}

uint16_t sram_readstrn(void* buf, uint32_t addr, uint16_t size) {
  uint16_t elemcount = 0;
  uint16_t count = size;
  uint8_t* tgt = buf;
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88);   /* READ */
  while(count--) {
    FPGA_WAIT_RDY();
    if(!(*(tgt++) = FPGA_RX_BYTE())) break;
    elemcount++;
  }
  tgt--;
  if(*tgt) *tgt = 0;
  FPGA_DESELECT();
  return elemcount;
}

uint16_t sram_writestrn(void* buf, uint32_t addr, uint16_t size) {
  uint16_t elemcount = 0;
  uint16_t count = size;
  uint8_t *src = buf;
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);   /* WRITE */
  if(*src) {
    while(count > 1) {
      FPGA_TX_BYTE(*src++);
      FPGA_WAIT_RDY();
      elemcount++;
      count--;
      if(!(*src)) break;
    }
  }
  FPGA_TX_BYTE(0);
  FPGA_WAIT_RDY();
  FPGA_DESELECT();
  return elemcount;
}

uint16_t sram_writeblock(void* buf, uint32_t addr, uint16_t size) {
  uint16_t count = size;
  uint8_t* src = buf;
  set_mcu_addr(addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);   /* WRITE */
  while(count--) {
    FPGA_TX_BYTE(*src++);
    FPGA_WAIT_RDY();
  }
  FPGA_DESELECT();
  return size;
}

char current_filename[258];
uint8_t gbc_launch_stage;

#ifdef CONFIG_MK3_STM32
#define GBC_LOAD_PACE_BEGIN() spi_gbc_load_begin()
#define GBC_LOAD_PACE_END() spi_gbc_load_end()
#define GBC_LOAD_DWT_USED() spi_gbc_load_dwt_used()
#define GBC_LOAD_DWT_FALLBACKS() spi_gbc_load_fallbacks()
#else
#define GBC_LOAD_PACE_BEGIN() ((void)0)
#define GBC_LOAD_PACE_END() ((void)0)
#define GBC_LOAD_DWT_USED() 0u
#define GBC_LOAD_DWT_FALLBACKS() 0u
#endif

/* C16 pre-start profiling only. No live-game polling or save-file writes.
 * 100 Hz ticks; modular subtraction is valid for these bounded launch times.
 * SD report is best effort, create-new, before RUN. Its own I/O and first
 * visible frame are deliberately excluded from the measured total. */
static struct {
  tick_t start, last, stage[5], copy[2][4], elapsed;
  uint32_t bytes[2],duplex_blocks;
  tick_t duplex_ticks;uint8_t duplex_used;
} gbc_load_profile;
static void gbc_profile_mark(unsigned stage) {
  tick_t now=getticks();
  gbc_load_profile.stage[stage]=(tick_t)(now-gbc_load_profile.last);
  gbc_load_profile.last=now;
}
static uint8_t gbc_profile_report(uint8_t success) {
  if(!gbc_file_logs_enabled)return 1; /* Disabled report is not a load failure. */
  char text[1024],path[48];FIL f;UINT written=0;FRESULT res=FR_EXIST;
  int len=snprintf(text,sizeof(text),
    "GBCLOAD1\ncandidate=G13C44\nsuccess=%u\nlaunch_stage=%u\nclock_hz=%u\n"
    "handoff_reset_ticks=%u\nfpga_ticks=%u\nrenderer_ticks=%u\ngame_ticks=%u\nsave_setup_ticks=%u\n"
    "renderer_bytes=%lu\ngame_bytes=%lu\n"
    "renderer_sd_ticks=%u\nrenderer_write_ticks=%u\nrenderer_readback_ticks=%u\nrenderer_compare_crc_ticks=%u\n"
    "game_sd_ticks=%u\ngame_write_ticks=%u\ngame_readback_ticks=%u\ngame_compare_ticks=%u\n"
    "elapsed_before_report_ticks=%u\ngame_crc=verified_rom_identity\nfull_readback=1\n"
    "report_io_included=0\nfirst_visible_frame=not_measured\nload_gap_min_ns=500\nload_dwt_used=%u\nload_dwt_fallbacks=%u\ngame_duplex_used=%u\ngame_duplex_ticks=%u\ngame_duplex_blocks=%lu\n",
    success,gbc_launch_stage,HZ,
    gbc_load_profile.stage[0],gbc_load_profile.stage[1],gbc_load_profile.stage[2],gbc_load_profile.stage[3],gbc_load_profile.stage[4],
    (unsigned long)gbc_load_profile.bytes[0],(unsigned long)gbc_load_profile.bytes[1],
    gbc_load_profile.copy[0][0],gbc_load_profile.copy[0][1],gbc_load_profile.copy[0][2],gbc_load_profile.copy[0][3],
    gbc_load_profile.copy[1][0],gbc_load_profile.copy[1][1],gbc_load_profile.copy[1][2],gbc_load_profile.copy[1][3],gbc_load_profile.elapsed,
    GBC_LOAD_DWT_USED(),GBC_LOAD_DWT_FALLBACKS(),gbc_load_profile.duplex_used,
    gbc_load_profile.duplex_ticks,(unsigned long)gbc_load_profile.duplex_blocks);
  if(len<0||(unsigned)len>=sizeof(text))return 0;
  if(check_or_create_folder("/sd2snes/gbcload/")!=FR_OK)return 0;
  for(unsigned i=0;i<1000;i++) {
    snprintf(path,sizeof(path),"/sd2snes/gbcload/load%03u.txt",i);
    res=f_open(&f,(const TCHAR *)path,FA_WRITE|FA_CREATE_NEW);
    if(res!=FR_EXIST)break;
  }
  if(res!=FR_OK)return 0;
  uint8_t ok=f_write(&f,text,(UINT)len,&written)==FR_OK&&written==(UINT)len;
  if(ok)ok=f_sync(&f)==FR_OK;
  res=f_close(&f);
  return ok&&res==FR_OK;
}

/* C26 loading UI: bit14 gives SNES SRAM ownership without starting GBC.
 * D1/D2 transactions remain atomic; updates occur only between verified blocks. */
static uint8_t gbc_ui_started,gbc_ui_last;
static uint32_t gbc_ui_size;
static void gbc_ui_status(uint8_t value) {
  if(!gbc_ui_started||value==gbc_ui_last)return;
  fpga_set_chipfeat(0x4000u|value);gbc_ui_last=value;
}
static void gbc_ui_progress(uint32_t verified) {
  if(gbc_ui_size)gbc_ui_status((uint8_t)((verified*100u)/gbc_ui_size));
}

/* Copy through the deployed MCU endpoint and compare every block read back.
 * Unlike calc_sram_crc(), this is valid while we hold the SNES in reset. */
static uint32_t gbc_verified_rom_crc;
static uint8_t gbc_copy_verified(uint8_t *filename, uint32_t address,
                                 uint32_t expected_size, uint32_t expected_crc) {
  uint8_t verify[512];
  unsigned section=address==0?1:0;
  tick_t mark;
  uint32_t total = 0, crc = crc32_init();
  file_open(filename, FA_READ);
  if(file_res) return 0;
  if(file_handle.fsize != expected_size) { file_close(); return 0; }
  for(;;) {
    mark=getticks();
    UINT count = file_read();
    gbc_load_profile.copy[section][0]+=(tick_t)(getticks()-mark);
    if(file_res) { file_close(); return 0; }
    if(!count) break;
    if(count > sizeof(verify) || count > expected_size - total) {
      file_close(); return 0;
    }
    mark=getticks();
    sram_writeblock(file_buf, address + total, count);
    gbc_load_profile.copy[section][1]+=(tick_t)(getticks()-mark);
    mark=getticks();
    sram_readblock(verify, address + total, count);
    gbc_load_profile.copy[section][2]+=(tick_t)(getticks()-mark);
    mark=getticks();
    if(memcmp(file_buf, verify, count)) { file_close(); return 0; }
    if(expected_crc||section) {
      for(UINT i = 0; i < count; i++) crc = crc32_update(crc, verify[i]);
    }
    gbc_load_profile.copy[section][3]+=(tick_t)(getticks()-mark);
    gbc_load_profile.bytes[section]+=count;
    total += count;
    if(section)gbc_ui_progress(total);
  }
  file_close();
  if(section)gbc_verified_rom_crc=crc32_finalize(crc);
  return total == expected_size &&
         (!expected_crc || crc32_finalize(crc) == expected_crc);
}


/* Fixed 512B game blocks; previous block is fully written before verification.
 * Static private buffers stay valid even on an aborted DMA transaction. */
static uint8_t gbc_copy_duplex(uint8_t *filename,uint32_t expected_size) {
  static uint8_t previous[512] __attribute__((aligned(4)));
  static uint8_t verify[512] __attribute__((aligned(4)));
  uint32_t total=0,crc=crc32_init();tick_t mark;UINT count;
  file_open(filename,FA_READ);
  if(file_res)return 0;
  if(!expected_size||expected_size>0x400000u||(expected_size&511u)||file_handle.fsize!=expected_size)goto fail;
  if(!spi_gbc_duplex_begin())goto fail;
  gbc_load_profile.duplex_used=1;
  while(total<expected_size) {
    mark=getticks();count=file_read();gbc_load_profile.copy[1][0]+=(tick_t)(getticks()-mark);
    if(file_res||count!=512)goto fail;
    mark=getticks();uint8_t ok=spi_gbc_duplex_block(0xd1,file_buf,verify);
    gbc_load_profile.duplex_ticks+=(tick_t)(getticks()-mark);
    if(!ok)goto fail;
    gbc_load_profile.duplex_blocks++;
    mark=getticks();
    if(total) {
      if(memcmp(previous,verify,512))goto fail;
      for(unsigned i=0;i<512;i++)crc=crc32_update(crc,verify[i]);
      gbc_load_profile.bytes[1]+=512;
      gbc_ui_progress(gbc_load_profile.bytes[1]);
    }
    memcpy(previous,file_buf,512);total+=512;
    gbc_load_profile.copy[1][3]+=(tick_t)(getticks()-mark);
  }
  mark=getticks();count=file_read();gbc_load_profile.copy[1][0]+=(tick_t)(getticks()-mark);
  if(file_res||count)goto fail;
  mark=getticks();uint8_t ok=spi_gbc_duplex_block(0xd2,previous,verify);
  gbc_load_profile.duplex_ticks+=(tick_t)(getticks()-mark);
  if(!ok)goto fail;
  gbc_load_profile.duplex_blocks++;
  mark=getticks();if(memcmp(previous,verify,512))goto fail;
      for(unsigned i=0;i<512;i++)crc=crc32_update(crc,verify[i]);
  gbc_load_profile.bytes[1]+=512;
  gbc_load_profile.copy[1][3]+=(tick_t)(getticks()-mark);
  gbc_ui_progress(gbc_load_profile.bytes[1]);
  file_close();gbc_verified_rom_crc=crc32_finalize(crc);return total==expected_size&&gbc_load_profile.bytes[1]==expected_size;
fail:
  file_close();return 0;
}

/* The replacement FPGA has no legacy $2a00 command RAM or reset hook.
 * Only the PRE-reconfiguration handshake uses the menu. Thereafter the MCU
 * releases SNES reset for the verified loading UI; GBC RUN stays clear until
 * the game/save payloads and masks are installed. */
static uint32_t gbc_load_rom(uint8_t *filename, uint32_t game_size,
                             uint32_t renderer_size, uint8_t flags) {
#ifdef GBC_SAVE_G12
  gbc_save_disarm();
#endif
#ifdef GBC_DUMP_G12
  gbc_dump_disarm();
#endif
  gbc_ui_started=0;gbc_ui_last=0;gbc_ui_size=game_size;
  memset(&gbc_load_profile,0,sizeof(gbc_load_profile));
  gbc_load_profile.start=gbc_load_profile.last=getticks();
  gbc_launch_stage = 1;
  if(flags & LOADROM_WAIT_SNES) {
    tick_t start = getticks();
    snes_set_snes_cmd(0x55);
    while(snes_get_mcu_cmd() != SNES_CMD_FPGA_RECONF) {
      if((tick_t)(getticks() - start) >= MS_TO_TICKS(2000)) {
        printf("GBC: menu handoff timeout\n");
        goto failed;
      }
    }
    /* Finish the stock menu fade/PPU cleanup while its FPGA and command
     * RAM still exist. The dedicated core cannot complete this handshake. */
    snes_set_snes_cmd(0x77);
    start = getticks();
    while(snes_get_mcu_cmd() != SNES_CMD_RESET) {
      if((tick_t)(getticks() - start) >= MS_TO_TICKS(2000)) {
        printf("GBC: menu screen cleanup timeout\n");
        goto failed;
      }
    }
  }
  snes_reset(1);
  delay_ms(SNES_RESET_PULSELEN_MS);
  gbc_profile_mark(0);
  gbc_launch_stage = 2;
  printf("GBC: configure\n");
  fpga_pgm((uint8_t *)FPGA_EGBC);
  if(file_res || !fpga_config || strcmp((const char *)fpga_config, (const char *)FPGA_EGBC) ||
     fpga_test() != FPGA_TEST_TOKEN) goto failed;
  fpga_set_chipfeat(0);
  gbc_profile_mark(1);
  GBC_LOAD_PACE_BEGIN();
  FPGA_SELECT(); FPGA_TX_BYTE(0xd4);
  uint8_t ram_protocol = FPGA_RX_BYTE(); FPGA_DESELECT();
  if(ram_protocol != 0xdf) goto failed;
  gbc_launch_stage = 3;
  printf("GBC: renderer SRAM write/readback\n");
  if(!gbc_copy_verified((uint8_t *)SGBSR, 0x890000, renderer_size,
                       GBC_RENDERER_CRC32)) goto failed;
  gbc_profile_mark(2);
  fpga_set_chipfeat(0x4000);gbc_ui_started=1;
  snes_reset(0);
  printf("GBC: game PSRAM write/readback\n");
  gbc_launch_stage = 4;
  if(game_size&&game_size<=0x400000u&&!(game_size&511u)) {
    if(!gbc_copy_duplex(filename,game_size))goto failed;
  } else if(!gbc_copy_verified(filename,0,game_size,0))goto failed;
  GBC_LOAD_PACE_END();
  gbc_profile_mark(3);
  romprops.ramsize_bytes = sgb_romprops.ramsize_bytes;
  romprops.sramsize_bytes = sgb_romprops.sramsize_bytes;
  romprops.srambase = sgb_romprops.srambase;
  romprops.has_msu1 = 0;
  set_rom_mask(sgb_romprops.romsize_bytes ? sgb_romprops.romsize_bytes - 1 : 0);
  set_saveram_mask(romprops.ramsize_bytes ? romprops.ramsize_bytes - 1 : 0);
  set_mapper(sgb_romprops.mapper_id);
  gbc_launch_stage = 5;
  gbc_ui_status(101);
  if((flags & LOADROM_WITH_SRAM) || !romprops.ramsize_bytes) {
#ifdef GBC_SAVE_G12
    if(!gbc_save_load(filename,romprops.ramsize_bytes,sgb_romprops.has_rtc)) goto failed;
#else
    sram_memset(SRAM_SAVE_ADDR, romprops.ramsize_bytes, 0xff);
    migrate_and_load_srm(filename, SRAM_SAVE_ADDR);
    if(file_res == FR_NO_FILE) file_res = 0;
    if(file_res) goto failed;
#endif
  }
#ifdef GBC_DUMP_G12
  gbc_dump_arm(filename);
#endif
  gbc_menu_bind_state(game_size,gbc_verified_rom_crc,romprops.ramsize_bytes);
  saveram_crc_old = 0;
  saveram_crc = 0;
  saveram_offset = 0;
  sram_crc_valid = 0;
  sram_crc_init = 1;
  sram_crc_romsize = game_size;
  readled(0);
  /* No init(): stock hooks/save-state clearing do not belong to this core.
   * Start the GBC only after the masks and SaveRAM have been installed. */
  gbc_profile_mark(4);
  gbc_ui_status(102);
  printf("GBC: start\n");
  gbc_load_profile.elapsed=(tick_t)(getticks()-gbc_load_profile.start);
  if(!gbc_profile_report(1))printf("GBC: load timing report unavailable\n");
  gbc_launch_stage = 6;
  snes_reset(1);delay_ms(SNES_RESET_PULSELEN_MS);
  fpga_set_chipfeat(sgb_romprops.fpga_sgbfeat);
  gbc_ui_started=0;
  snes_reset(0);
#ifdef GBC_DIAGNOSTIC
  /* Calls returned; this is NOT an acknowledgement from either CPU. */
  gbc_launch_stage = 7;
  /* Suppress prepare_reset() save flush as well as background saving.
   * The FPGA's already-installed SaveRAM and mask remain unchanged. */
  romprops.sramsize_bytes = 0;
#endif
  return game_size;

failed:
  GBC_LOAD_PACE_END();
#ifdef GBC_DUMP_G12
  gbc_dump_disarm();
#endif
#ifdef GBC_SAVE_G12
  gbc_save_disarm();
#endif
  gbc_launch_stage |= 0x80;
  if(gbc_ui_started){gbc_ui_status(gbc_launch_stage);delay_ms(3000);}
  gbc_ui_started=0;
  gbc_load_profile.elapsed=(tick_t)(getticks()-gbc_load_profile.start);
  (void)gbc_profile_report(0);
  printf("GBC: launch failed, restoring menu\n");
  snes_reset(1);
  delay_ms(SNES_RESET_PULSELEN_MS);
  load_rom((uint8_t *)MENU_FILENAME, SRAM_MENU_ADDR,
           LOADROM_WITH_FPGA | LOADROM_WITH_RESET);
  return 0;
}

uint32_t load_rom(uint8_t* filename, uint32_t base_addr, uint8_t flags) {
  UINT bytes_read;
  DWORD filesize;
  UINT count=0;
  uint8_t is_menu = (filename == (uint8_t*)MENU_FILENAME);
  tick_t ticksstart, ticks_total=0;
  ticksstart=getticks();

  /* Drop stale dedicated-core state on every menu/stock/EGBC transition. */
#ifdef GBC_SAVE_G12
  gbc_save_disarm();
#endif
#ifdef GBC_DUMP_G12
  gbc_dump_disarm();
#endif
  sgb_romprops.has_sgb = sgb_romprops.has_egbc = 0;

  // copy the full name and path
  strncpy(current_filename, (char *)filename, sizeof(current_filename)-1);

  printf("%s\n", filename);
  file_open(filename, FA_READ);
  if(file_res) {
    uart_putc('?');
    uart_putc(0x30+file_res);
    return 0;
  }
  filesize = file_handle.fsize; // won't be correct for combo roms
  
  uint32_t file_offset = 0;
  if(flags & LOADROM_WITH_COMBO) {
    printf("Combo Header Check...");
    // seek to the proper slot.  slots are naturally aligned on 1MB boundaries.
    file_offset = 0x100000 * snescmd_readbyte(SNESCMD_MCU_CMD + 1);
    printf(" file_offset=0x%lx", file_offset);
    printf(" OK.\n");
  }

  /* SGB detect and file management */
  uint8_t *sgb_filename = filename;
  DWORD sgb_filesize = file_handle.fsize;
  sgb_id(&sgb_romprops, sgb_filename);
  if (!sgb_update_file(&filename)) return 0;

  filesize = file_handle.fsize;
  smc_id(&romprops, file_offset);
  file_close();

  if(flags & LOADROM_WITH_COMBO) {
    printf("Combo Transition...");
    uint32_t romslot = snescmd_readbyte(SNESCMD_MCU_CMD + 1);
    romprops.offset += romslot << 20;
    printf(" romslot=0x%lx", romslot);
    printf(" offset=0x%lx", romprops.offset);
    
    // force has_combo since only slot 00 has the matching carttype
    romprops.has_combo = 1;
    printf(" OK.\n");
  }

  /* SGB assign the SGB FPGA file and relocate the snes image to the 512KB RAM */
  if (!sgb_update_romprops(&romprops, sgb_filename)) return 0;

  if(sgb_romprops.has_egbc) {
    return gbc_load_rom(sgb_filename, sgb_filesize, filesize, flags);
  }

  uint16_t fpga_features_preload = romprops.fpga_features | FEAT_CMD_UNLOCK | FEAT_2100_LIMIT_NONE;
  if(is_menu) {
    printf("Setting menu features...");
    fpga_set_features(fpga_features_preload);
    printf("OK.\n");
  }
  /* TODO check prerequisites and set error code here */
  if(flags & LOADROM_WAIT_SNES) {
    printf("Setting cmd=0x55...");
    snes_set_snes_cmd(0x55);
    printf("OK.\n");
  }
  /* reconfigure FPGA if necessary */
  if(flags & LOADROM_WAIT_SNES) {
    printf("Checking if ok to reconfigure...");
    while(snes_get_mcu_cmd() != SNES_CMD_FPGA_RECONF);
    printf("OK.\n");
  }
  if(romprops.fpga_conf || (flags & LOADROM_WITH_FPGA)) {
    const uint8_t *fpga_conf = romprops.fpga_conf ? romprops.fpga_conf : FPGA_BASE;
    printf("reconfigure FPGA with %s...\n", fpga_conf);
    fpga_pgm((uint8_t*)fpga_conf);
    fpga_set_features(fpga_features_preload);
  }
  if(flags & LOADROM_WAIT_SNES) snes_set_snes_cmd(0x77);
  uint32_t total_bytes_read = 0;
  {
    set_mcu_addr(base_addr + romprops.load_address);
    file_open(filename, FA_READ);
    ff_sd_offload=1;
    sd_offload_tgt=0;
    f_lseek(&file_handle, romprops.offset);
    for(;;) {
      ff_sd_offload=1;
      sd_offload_tgt=0;
      bytes_read = file_read();
      if (file_res || !bytes_read) break;
      if(!(count++ % 512)) {
        uart_putc('.');
      }
      total_bytes_read += bytes_read;
      // FIXME: can we do this in the general (non-combo) case?
      // FIXME: what does the condition below do that doubles romsize_bytes until it hits the file limit?  Do some games
      // misreport size?  Or is this for BSX?
      if((flags & LOADROM_WITH_COMBO) && (total_bytes_read >= romprops.romsize_bytes)) break;
    }
    file_close();
  }
  uart_putc('\n');

  printf("rom header map: %02x; mapper id: %d\n", romprops.header.map, romprops.mapper_id);
  ticks_total=getticks()-ticksstart;
  printf("%u ticks total\n", ticks_total);
  if(romprops.mapper_id==3) {
    printf("BSX Flash cart image\n");
    printf("attempting to load BSX BIOS /sd2snes/bsxbios.bin...\n");
    load_sram_offload((uint8_t*)"/sd2snes/bsxbios.bin", 0x800000, LOADRAM_AUTOSKIP_HEADER);
    printf("attempting to load BS data file /sd2snes/bsxpage.bin...\n");
    load_sram_offload((uint8_t*)"/sd2snes/bsxpage.bin", 0x900000, 0);
    printf("Type: %02x\n", romprops.header.destcode);
    set_bsx_regs(0xf6, 0x09);
    uint16_t rombase;
    if(romprops.header.ramsize & 1) {
      rombase = romprops.load_address + 0xff00;
// set_bsx_regs(0x36, 0xc9);
    } else {
      rombase = romprops.load_address + 0x7f00;
// set_bsx_regs(0x34, 0xcb);
    }
    sram_writebyte(0x33, rombase+0xda);
    sram_writebyte(0x00, rombase+0xd4);
    sram_writebyte(0x00, rombase+0xd5);
    if(CFG.bsx_use_usertime) {
      set_fpga_time(srtctime2bcdtime(CFG.bsx_time));
    } else {
      set_fpga_time(get_bcdtime());
    }
  }
  if(romprops.has_dspx) {
    printf("DSPx game. Loading firmware image %s...\n", romprops.dsp_fw);
    load_dspx(romprops.dsp_fw, romprops.fpga_features);
    /* fallback to DSP1B firmware if DSP1.bin is not present */
    if(file_res && romprops.dsp_fw == DSPFW_DSP1) {
      load_dspx(DSPFW_DSP1B, romprops.fpga_features);
    }
    if(file_res) {
      snes_menu_errmsg(MENU_ERR_SUPPLFILE, (void*)romprops.dsp_fw);
    }
  }
  uint32_t rammask;
  uint32_t rommask;

  while(!romprops.has_combo && filesize > (romprops.romsize_bytes + romprops.offset)) {
    romprops.romsize_bytes <<= 1;
  }

  if (romprops.has_sa1 && romprops.header.carttype == 0x36 && romprops.header.ramsize) {
    // move iram into saveram for special carts with no bwram
    romprops.header.ramsize = 1;
    romprops.ramsize_bytes = 0x800;
    // override any changes to this so we capture full sram
    romprops.srambase       = 0;
    romprops.sramsize_bytes = romprops.ramsize_bytes;
    rammask = 1;
  } else if(romprops.header.ramsize == 0) {
    rammask = 0;
  } else {
    rammask = romprops.ramsize_bytes - 1;
  }
  rommask = romprops.romsize_bytes - 1;
  
  uint8_t ramslot = 0;
  if (romprops.has_combo) {
    ramslot = sram_readbyte((romprops.mapper_id == 0 || romprops.mapper_id == 2) ? 0xFFDA : 0x7FDA);
  }
  
  printf("ramsize=%x ramslot=%hx rammask=%lx\nromsize=%x rommask=%lx\n", romprops.header.ramsize, ramslot, rammask, romprops.header.romsize, rommask);

  /* SGB setup romprops and load SRAM */
  sgb_load_sram(sgb_filename);

  /* SGB update local file properties */
  if (sgb_romprops.has_sgb) {
    /* reset the filename to match the GB file */
    filename = sgb_filename;
    filesize = sgb_filesize;

    /* update SaveRAM properties */
    romprops.ramsize_bytes = (CFG.sgb_enable_state && sgb_romprops.ramsize_bytes <= 64 * 1024) ? (128 * 1024) : sgb_romprops.ramsize_bytes;
    romprops.srambase = sgb_romprops.srambase;
    romprops.sramsize_bytes = (CFG.sgb_enable_state && sgb_romprops.ramsize_bytes <= 64 * 1024) ? (128 * 1024) : sgb_romprops.sramsize_bytes;

    rammask = sgb_romprops.ramsize_bytes ? (sgb_romprops.ramsize_bytes - 1) : 0;
    rommask = sgb_romprops.romsize_bytes ? (sgb_romprops.romsize_bytes - 1) : 0;
  }

  /* SGB load GB RTC */
  sgb_gtc_load(sgb_filename);

  printf("ramsize=%x rammask=%lx\nromsize=%x rommask=%lx\n", romprops.header.ramsize, rammask, romprops.header.romsize, rommask);
  set_saveram_mask(rammask);
  // don't set these for special chips as it may break from not supporting the feature
  if (  !romprops.fpga_conf
      || romprops.fpga_conf == FPGA_BASE
      || romprops.fpga_conf == FPGA_DSP) {
      set_saveram_base(ramslot);
  }
  set_rom_mask(rommask);
  readled(0);

  printf("gsu=%x sa1=%x srambase=%lx sramsize=%lx\n", romprops.has_gsu, romprops.has_sa1, romprops.srambase, romprops.sramsize_bytes);
  if(flags & LOADROM_WITH_SRAM) {
    if(romprops.ramsize_bytes) {
      // powerslide relies on the init value to be 00.
      sram_memset(SRAM_SAVE_ADDR, romprops.ramsize_bytes, romprops.has_gsu ? 0x00 : 0xFF);
      if (romprops.sramsize_bytes) migrate_and_load_srm(filename, SRAM_SAVE_ADDR);
      /* file not found error is ok (SRM file might not exist yet) */
      if(file_res == FR_NO_FILE) file_res = 0;
      saveram_crc_old = calc_sram_crc(SRAM_SAVE_ADDR + romprops.srambase, romprops.sramsize_bytes, 0);
      saveram_crc = 0;
      saveram_offset = 0;
    } else {
      printf("No SRAM\n");
    }
  }

  printf("check MSU...");
  if(msu1_check(filename)) {
    romprops.fpga_features |= FEAT_MSU1;
    romprops.has_msu1 = 1;
  } else {
    romprops.has_msu1 = 0;
  }
  printf("done\n");

  printf("r213fen=%d is_u16=%d filename=%s\n", cfg_is_r213f_override_enabled(), STS.is_u16, filename);
  if(cfg_is_r213f_override_enabled() && !is_menu && !STS.is_u16) {
    romprops.fpga_features |= FEAT_213F; /* e.g. for general consoles */
  }
  fpga_set_213f(romprops.region);
//  fpga_set_features(romprops.fpga_features);
  fpga_set_chipfeat(sgb_romprops.has_sgb ? sgb_romprops.fpga_sgbfeat : romprops.fpga_dspfeat);
  fpga_set_dac_boost(CFG.msu_volume_boost);
  dac_pause();
  dac_reset(0);
/* fully enable pair mode again instead of just setting the video/d4 mode
   in case previous pair mode entry was skipped / pair mode undetected so far */
  if(get_cic_state() == CIC_PAIR) {
    if(!is_menu) {
      if(CFG.vidmode_game == VIDMODE_AUTO) {
        cic_pair(romprops.region, romprops.region);
      } else {
        cic_pair(CFG.vidmode_game, romprops.region);
      }
    }
  }

  if(cfg_is_onechip_transient_fixes() && !is_menu) {
    romprops.fpga_features |= FEAT_2100;
  }
  romprops.fpga_features |= FEAT_2100_LIMIT(cfg_get_brightness_limit());

  /* enable Satellaview Base emulation only if no physical Satellaview Base unit is present */
  if(!STS.has_satellaview) {
    romprops.fpga_features |= FEAT_SATELLABASE;
  }

  if(flags & LOADROM_WAIT_SNES) {
    while(snes_get_mcu_cmd() != SNES_CMD_RESET) cli_entrycheck();
  }

  set_mapper(sgb_romprops.has_sgb ? sgb_romprops.mapper_id : romprops.mapper_id);

  if (romprops.has_combo) {
    static uint32_t combo_srambase = 0;
    static uint32_t combo_sramsize_bytes = 0;
  
    // set version number
    snescmd_writebyte(COMBO_VERSION, SNESCMD_COMBO_VERSION);
  
    if (flags & LOADROM_WITH_COMBO) {
      // restore proper bounds
      romprops.srambase = combo_srambase;
      romprops.sramsize_bytes = combo_sramsize_bytes;
    } else {
      // base ROM.
      // set base unlock features.
      snescmd_writebyte(0x1, SNESCMD_MAP);
      // record the saveram properties
      combo_srambase = romprops.srambase;
      combo_sramsize_bytes = romprops.sramsize_bytes;
    }

    // enable use of the DMA unit
    romprops.fpga_features |= FEAT_DMA1;
  }

//printf("%04lx\n", romprops.header_address + ((void*)&romprops.header.vect_irq16 - (void*)&romprops.header));
  if(flags & (LOADROM_WITH_RESET|LOADROM_WAIT_SNES)) {
    assert_reset();
    init(filename);
    deassert_reset();
  }
  // loading a new rom implies the previous crc is no longer valid
  sram_crc_valid = romprops.has_combo ? 1 : 0;
  sram_crc_init = 1;
  sram_crc_romsize = filesize - romprops.offset;

  return (uint32_t)filesize;
}

void assert_reset() {
  printf("resetting SNES\n");
  fpga_dspx_reset(1);
  snes_reset(1);
  if(STS.is_u16 && (STS.u16_cfg & 0x01)) {
    delay_ms(60*SNES_RESET_PULSELEN_MS);
  } else {
    delay_ms(SNES_RESET_PULSELEN_MS);
  }
}

void init(uint8_t *filename) {
  snescmd_prepare_nmihook();
  if (CFG.reset_patch) snescmd_writebyte(0, SNESCMD_RESET_HOOK+1);
  cheat_yaml_load(filename);
// XXX    cheat_yaml_save(filename);
  cheat_program();
  savestate_program();
  fpga_set_features(romprops.fpga_features);
  fpga_reset_srtc_state();
  snes_set_mcu_cmd(0);
  // init save state region - VRAM, APURAM, CGRAM, OAM only
  sram_memset(0xF70000, 0x30000, 0);
}

void deassert_reset() {
  snes_reset(0);
  fpga_dspx_reset(0);
  // handle reset loop from hook
  snes_reset_loop();
}

uint32_t load_spc(uint8_t* filename, uint32_t spc_data_addr, uint32_t spc_header_addr) {
  DWORD filesize;
  UINT bytes_read;
  uint8_t data;
  UINT j;

  printf("%s\n", filename);

  file_open(filename, FA_READ); /* Open SPC file */
  if(file_res) return 0;
  filesize = file_handle.fsize;
  if (filesize < 65920) { /* At this point, we care about filesize only */
    file_close(); /* since SNES decides if it is an SPC file */
    sram_writebyte(0, spc_header_addr); /* If file is too small, destroy previous SPC header */
    return 0;
  }

  set_mcu_addr(spc_data_addr);
  f_lseek(&file_handle, 0x100L); /* Load 64K data segment */

  for(;;) {
    bytes_read = file_read();
    if (file_res || !bytes_read) break;
    FPGA_SELECT();
    FPGA_TX_BYTE(0x98);
    for(j=0; j<bytes_read; j++) {
      FPGA_TX_BYTE(file_buf[j]);
      FPGA_WAIT_RDY();
    }
    FPGA_DESELECT();
  }

  file_close();
  file_open(filename, FA_READ); /* Reopen SPC file to reset file_getc state*/

  set_mcu_addr(spc_header_addr);
  f_lseek(&file_handle, 0x0L); /* Load 256 bytes header */

  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);
  for (j = 0; j < 256; j++) {
    data = file_getc();
    FPGA_TX_BYTE(data);
    FPGA_WAIT_RDY();
  }
  FPGA_DESELECT();

  file_close();
  file_open(filename, FA_READ); /* Reopen SPC file to reset file_getc state*/

  set_mcu_addr(spc_header_addr+0x100);
  f_lseek(&file_handle, 0x10100L); /* Load 128 DSP registers */

  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);
  for (j = 0; j < 128; j++) {
    data = file_getc();
    FPGA_TX_BYTE(data);
    FPGA_WAIT_RDY();
  }
  FPGA_DESELECT();
  file_close(); /* Done ! */

  /* clear echo buffer to avoid artifacts */
  uint8_t esa = sram_readbyte(spc_header_addr+0x100+0x6d);
  uint8_t edl = sram_readbyte(spc_header_addr+0x100+0x7d);
  uint8_t flg = sram_readbyte(spc_header_addr+0x100+0x6c);
  if(!(flg & 0x20) && (edl & 0x0f)) {
    int echo_start = esa << 8;
    int echo_length = (edl & 0x0f) << 11;
    printf("clearing echo buffer %04x-%04x...\n", echo_start, echo_start+echo_length-1);
    sram_memset(spc_data_addr+echo_start, echo_length, 0);
  }

  return (uint32_t)filesize;
}

uint32_t load_sram_offload(uint8_t* filename, uint32_t base_addr, uint8_t flags) {
  set_mcu_addr(base_addr);
  UINT bytes_read;
  DWORD filesize;
  file_open(filename, FA_READ);
  filesize = file_handle.fsize;
  if(file_res) return 0;
  if(flags & LOADRAM_AUTOSKIP_HEADER) {
    if((filesize & 0xffff) == 0x200) {
      ff_sd_offload=1;
      f_lseek(&file_handle, 0x200L);
      printf("load_sram_offload: skipping 512b header\n");
    }
  }
  if(file_res) return 0;
  for(;;) {
    ff_sd_offload=1;
    sd_offload_tgt=0;
    bytes_read = file_read();
    if (file_res || !bytes_read) break;
  }
  file_close();
  return (uint32_t)filesize;
}

uint32_t migrate_and_load_srm(uint8_t* filename, uint32_t base_addr) {
  uint8_t srmfile[256] = SAVE_BASEDIR;
  append_file_basename((char*)srmfile, (char*)filename, ".srm", sizeof(srmfile));
  printf("SRM file: %s\n", srmfile);

  uint32_t filesize;
  /* check for SRM file in new centralized sram folder */
  filesize = load_sram(srmfile, base_addr);
  if(file_res) {
    /* try to move SRM file from old place to new one and to load again */
    strcpy(strrchr((char*)filename, (int)'.'), ".srm");
    printf("%s not found, trying to load and migrate %s...\n", srmfile, filename);
    /* check if new sram folder exists, create it if it doesn't */
    check_or_create_folder(SAVE_BASEDIR);
    f_rename((TCHAR*)filename, (TCHAR*)srmfile);
    filesize = load_sram(srmfile, base_addr);
    if(file_res) {
      print_fresult(file_res, "migrate_and_load_sram: could not open %s\n", srmfile);
      return 0;
    }
  }
  return (uint32_t)filesize;
}

uint32_t load_sram(uint8_t* filename, uint32_t base_addr) {
  UINT bytes_read;
  DWORD filesize;

  set_mcu_addr(base_addr);
  file_open((uint8_t*)filename, FA_READ);
  filesize = file_handle.fsize;
  if(file_res) {
    printf("load_sram: could not open %s, res=%d\n", filename, file_res);
    return 0;
  }
  for(;;) {
    bytes_read = file_read();
    if (file_res || !bytes_read) break;
    FPGA_SELECT();
    FPGA_TX_BYTE(0x98);
    for(int j=0; j<bytes_read; j++) {
      FPGA_TX_BYTE(file_buf[j]);
      FPGA_WAIT_RDY();
    }
    FPGA_DESELECT();
  }
  file_close();
  return (uint32_t)filesize;
}

uint32_t load_sram_rle(uint8_t* filename, uint32_t base_addr) {
  uint8_t data;
  set_mcu_addr(base_addr);
  DWORD filesize;
  file_open(filename, FA_READ);
  filesize = file_handle.fsize;
  if(file_res) return 0;
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);
  for(;;) {
    data = rle_file_getc();
    if (file_res || file_status) break;
    FPGA_TX_BYTE(data);
    FPGA_WAIT_RDY();
  }
  FPGA_DESELECT();
  file_close();
  return (uint32_t)filesize;
}

uint32_t load_bootrle(uint32_t base_addr) {
  uint8_t data;
  set_mcu_addr(base_addr);
  DWORD filesize = 0;
  rle_mem_init(bootrle, sizeof(bootrle));

  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);
  for(;;) {
    data = rle_mem_getc();
    if(rle_state) break;
    FPGA_TX_BYTE(data);
    FPGA_WAIT_RDY();
    filesize++;
  }
  FPGA_DESELECT();
  return (uint32_t)filesize;
}

void save_srm(uint8_t* filename, uint32_t sram_size, uint32_t base_addr) {
    char srmfile[256] = SAVE_BASEDIR;
    check_or_create_folder(SAVE_BASEDIR);
    append_file_basename(srmfile, (char*)filename, ".srm", sizeof(srmfile));
    save_sram((uint8_t*)srmfile, sram_size, base_addr);
}

void save_sram(uint8_t* filename, uint32_t sram_size, uint32_t base_addr) {
  uint32_t remain = sram_size;
  size_t copy;
  FPGA_DESELECT();
  file_open(filename, FA_CREATE_ALWAYS | FA_WRITE);
  if(file_res) {
    uart_putc(0x30+file_res);
    return;
  }
  set_mcu_addr(base_addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x88); /* read */
  while(remain) {
    copy = (remain > 512) ? 512 : remain;
    for(int j=0; j < copy; j++) {
      FPGA_WAIT_RDY();
      file_buf[j] = FPGA_RX_BYTE();
    }
    file_write(copy);
    if(file_res) {
      uart_putc(0x30+file_res);
      return;
    }
    remain -= copy;
  }
  FPGA_DESELECT();
  file_close();
}

uint32_t calc_sram_crc(uint32_t base_addr, uint32_t size, uint32_t crc) {
  uint8_t data;
  uint32_t count;
  crc_valid=1;
  set_mcu_addr(base_addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(FPGA_CMD_READMEM | FPGA_MEM_AUTOINC);
  for(count=0; count<size; count++) {
    FPGA_WAIT_RDY();
    data = FPGA_RX_BYTE();
    if(get_snes_reset()) {
      crc_valid = 0;
      sram_crc_valid = romprops.has_combo ? 1 : 0;
      sram_crc_init = 1;
      break;
    }
    crc = crc32_update(crc, data);
  }
  FPGA_DESELECT();
  return crc;
}

uint8_t sram_reliable() {
  uint16_t score=0;
  uint32_t val;
  uint8_t result = 0;
  for(uint16_t i = 0; i < SRAM_RELIABILITY_SCORE; i++) {
    val=sram_readlong(SRAM_SCRATCHPAD);
    if(val==0x12345678) {
      score++;
    } else {
      printf("i=%d val=%08lX\n", i, val);
    }
  }
  if(score<SRAM_RELIABILITY_SCORE) {
    result = 0;
/* dprintf("score=%d\n", score); */
  } else {
    result = 1;
  }
  rdyled(result);
  return result;
}

void sram_memset(uint32_t base_addr, uint32_t len, uint8_t val) {
  set_mcu_addr(base_addr);
  FPGA_SELECT();
  FPGA_TX_BYTE(0x98);
  for(uint32_t i=0; i<len; i++) {
    FPGA_TX_BYTE(val);
    FPGA_WAIT_RDY();
  }
  FPGA_DESELECT();
}

void load_dspx(const uint8_t *filename, uint8_t coretype) {
  UINT bytes_read;
  uint16_t word_cnt;
  uint8_t wordsize_cnt = 0;
  uint16_t sector_remaining = 0;
  uint16_t sector_cnt = 0;
  uint16_t pgmsize = 0;
  uint16_t datsize = 0;
  uint32_t pgmdata = 0;
  uint16_t datdata = 0;

  if(coretype & FEAT_ST0010) {
    datsize = 1536;
    pgmsize = 2048;
  } else if (coretype & FEAT_DSPX) {
    datsize = 1024;
    pgmsize = 2048;
  } else {
    printf("load_dspx: unknown core (%02x)!\n", coretype);
  }

  file_open((uint8_t*)filename, FA_READ);
  if(file_res) {
    printf("Could not read %s: error %d\n", filename, file_res);
    return;
  }

  fpga_reset_dspx_addr();

  for(word_cnt = 0; word_cnt < pgmsize;) {
    if(!sector_remaining) {
      bytes_read = file_read();
      sector_remaining = bytes_read;
      sector_cnt = 0;
    }
    pgmdata = (pgmdata << 8) | file_buf[sector_cnt];
    sector_cnt++;
    wordsize_cnt++;
    sector_remaining--;
    if(wordsize_cnt == 3){
      wordsize_cnt = 0;
      word_cnt++;
      fpga_write_dspx_pgm(pgmdata);
    }
  }

  wordsize_cnt = 0;
  if(coretype & FEAT_ST0010) {
    file_seek(0xc000);
    sector_remaining = 0;
  }

  for(word_cnt = 0; word_cnt < datsize;) {
    if(!sector_remaining) {
      bytes_read = file_read();
      sector_remaining = bytes_read;
      sector_cnt = 0;
    }
    datdata = (datdata << 8) | file_buf[sector_cnt];
    sector_cnt++;
    wordsize_cnt++;
    sector_remaining--;
    if(wordsize_cnt == 2){
      wordsize_cnt = 0;
      word_cnt++;
      fpga_write_dspx_dat(datdata);
    }
  }

  fpga_reset_dspx_addr();

  file_close();

}
