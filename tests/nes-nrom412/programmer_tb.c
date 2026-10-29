// SPDX-License-Identifier: MIT
// Production programmer + FatFS, modeled GPIO/configuration device only.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "nes_diag_runtime.h"
#include "rle.h"
void nrom_fatdisk_prepare(const uint8_t *,uint32_t);
static struct nes_diag_report diag;
static uint8_t bytes[512];static unsigned nbytes,post,pins_masked,clocks,init_count;
static bool prog,done,fail_done,returned;
static FRESULT file_res;
static uint8_t gbc_spi_pacing;
static const uint8_t *fpga_config;
struct fake_reg {int GPIO_I;};static struct fake_reg reg;
#define FPGA_PROGBREG (&reg)
#define FPGA_PROGBBIT 0
#define BITBAND(v,b) (prog)
#define FPGA_DIN_MASK() (pins_masked=1)
#define FPGA_DIN_UNMASK() (pins_masked=0)
#define FPGA_SEND_BYTE_SERIAL(v) send_byte(v)
#define CCLK() tick()
static void send_byte(uint8_t value){assert(pins_masked&&nbytes<sizeof(bytes));bytes[nbytes++]=value;}
static void tick(void){if(++clocks==3 && !fail_done)done=true;}
static void fpga_init(void){init_count++;}
static void fpga_postinit(void){post++;}
static void fpga_set_prog_b(int v){prog=!!v;if(!v)done=false;}
static int fpga_get_initb(void){return prog;}
static int fpga_get_done(void){return done;}
struct nes_diag_wait nes_diag_wait_start(uint32_t ticks,uint32_t polls){(void)ticks;(void)polls;return (struct nes_diag_wait){0,0,0};}
bool nes_diag_wait_step(struct nes_diag_wait *w){return ++w->polls<400;}
void nes_diag_fail(enum nes_diag_error e){diag.error=e;}
const struct nes_diag_report *nes_diag_status(void){return &diag;}
bool nes_return_failed(void){return returned;}
bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;return true;}
#include "programmer.inc"
static void fresh(void){memset(&diag,0,sizeof(diag));memset(bytes,0,sizeof(bytes));nbytes=post=pins_masked=clocks=init_count=0;prog=done=fail_done=returned=false;fpga_config=0;}
int main(void){
 FATFS fs;uint8_t rom[24592]={0};nrom_fatdisk_prepare(rom,sizeof(rom));assert(f_mount(&fs,"",1)==FR_OK);
 fresh();diag.phase=NES_DIAG_RECOVER;assert(nes_diag_fpga_pgm((const uint8_t *)"base"));
 assert(nbytes==263 && bytes[0]==1 && bytes[1]==0xa4 && bytes[2]==0xa4 && bytes[3]==0xa4 && bytes[4]==0x9b);
 for(unsigned i=5;i<263;i++)assert(bytes[i]==0x66);
 assert(!pins_masked && done && prog && post==1 && file_res==FR_OK && fpga_config && init_count==1);
 fresh();assert(!nes_diag_fpga_pgm((const uint8_t *)"bad.bi3"));assert(diag.error==NES_DIAG_FPGA_FORMAT && !post && !pins_masked);
 fresh();fail_done=true;assert(!nes_diag_fpga_pgm((const uint8_t *)"base"));assert(diag.error==NES_DIAG_FPGA_DONE && !post && !pins_masked);
 fresh();assert(!nes_diag_fpga_pgm((const uint8_t *)"missing"));assert(diag.error==NES_DIAG_FPGA_OPEN && !init_count && !post);
 puts("PASS NROM412 actual programmer and FatFS: normal, malformed, DONE timeout, missing file; modeled GPIO");return 0;
}
