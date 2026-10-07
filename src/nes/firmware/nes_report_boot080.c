/* SPDX-License-Identifier: GPL-2.0-only */
#include <string.h>
#include "config.h"
#include "bits.h"
#include "fpga.h"
#include "fpga_spi.h"
#include "memory.h"
#include "snes.h"
#include "nes_menu_return.h"
#include "nes_report_boot080.h"
/* Sizes and output lengths are pinned by the080 materializer to079 inputs. */
extern const uint8_t cfgware[54754],bootrle[2811];
extern const uint8_t *fpga_config;
extern uint8_t gbc_spi_pacing;
extern int snes_boot_configured,sd_offload,ff_sd_offload,during_blocktrans;
int fpga_get_done(void); /* existing fpga.c export lacks a public prototype */
static bool owned(void) {
 return nes_diag_active()&&!nes_return_failed()&&!sd_offload&&!ff_sd_offload&&
  !during_blocktrans&&get_snes_reset()&&
  !(NVIC->ISER[(unsigned)OTG_FS_IRQn>>5]&(1u<<((unsigned)OTG_FS_IRQn&31)));
}
static bool fail(enum nes_diag_error e){snes_reset(1);nes_return_fail(e);return false;}
static bool pin(unsigned n,bool high,enum nes_diag_error e) {
 struct nes_diag_wait w=nes_diag_wait_start(100,5000000u);
 do {
  if(!nes_return_io_step())return false;
  bool v=n==0?!!BITBAND(FPGA_PROGBREG->GPIO_I,FPGA_PROGBBIT):n==1?!!fpga_get_initb():!!fpga_get_done();
  if(v==high)return true;
 }while(nes_diag_wait_step(&w));
 return fail(e);
}
static bool serial(void *unused,uint8_t b) {
 (void)unused;if(!nes_return_io_step())return false;
 FPGA_SEND_BYTE_SERIAL(b);return true;
}
struct boot_buffer {uint8_t bytes[256];unsigned used,done;};
static bool flush(struct boot_buffer *b) {
 uint8_t back[256];unsigned n=b->used;
 if(!n)return true;
 if(!owned()||!nes_return_io_step())return false;
 if(sram_writeblock(b->bytes,SRAM_MENU_ADDR+b->done,n)!=n||nes_return_failed())return false;
 if(sram_readblock(back,SRAM_MENU_ADDR+b->done,n)!=n||nes_return_failed()||memcmp(back,b->bytes,n))return false;
 b->done+=n;b->used=0;return true;
}
static bool bootbyte(void *ctx,uint8_t value) {
 struct boot_buffer *b=ctx;b->bytes[b->used++]=value;
 return b->used<sizeof(b->bytes)||flush(b);
}
bool report_line080(unsigned line,const char *text) {
 char data[33],back[33];
 if(!owned()||!snes_boot_configured||line>=24||!text||strlen(text)>32)return fail(NES_DIAG_MENU);
 memset(data,' ',32);data[32]=0;memcpy(data,text,strlen(text));
 if(!nes_return_io_step()||sram_writeblock(data,SRAM_CMD_ADDR+33*line,33)!=33||nes_return_failed())return fail(NES_DIAG_SPI);
 if(sram_readblock(back,SRAM_CMD_ADDR+33*line,33)!=33||nes_return_failed()||memcmp(data,back,33))return fail(NES_DIAG_SPI);
 return true;
}
bool report_boot080(void) {
 bool masked=false;struct boot_buffer b={0};
 if(!owned())return fail(NES_DIAG_MENU);
 snes_boot_configured=0;fpga_config=0;gbc_spi_pacing=0;
 fpga_init();fpga_set_prog_b(0);
 if(!pin(0,false,NES_DIAG_FPGA_PROG))goto failed;
 fpga_set_prog_b(1);
 if(!pin(1,true,NES_DIAG_FPGA_INIT)||!pin(2,false,NES_DIAG_FPGA_DONE))goto failed;
 FPGA_DIN_MASK();masked=true;
 if(!report_decode080(cfgware,sizeof(cfgware),153544,serial,0))goto failed;
 FPGA_DIN_UNMASK();masked=false;
 if(!nes_return_delay(1,true)||!pin(2,true,NES_DIAG_FPGA_DONE))goto failed;
 fpga_config=FPGA_ROM;fpga_postinit();
 if(!report_decode080(bootrle,sizeof(bootrle),65535,bootbyte,&b)||!flush(&b))goto failed;
 if(nes_return_failed())goto failed;
 set_saveram_mask(0x1fff);if(nes_return_failed())goto failed;
 set_rom_mask(0x3fffff);if(nes_return_failed())goto failed;
 set_mapper(7);if(nes_return_failed())goto failed;
 snes_boot_configured=1;
 for(unsigned line=0;line<24;line++)if(!report_line080(line,""))goto failed;
 return true; /* RESET still held; caller writes labels before release. */
failed:
 if(masked)FPGA_DIN_UNMASK();
 snes_boot_configured=0;fpga_config=0;
 return fail(NES_DIAG_FPGA_FORMAT);
}
