// SPDX-License-Identifier: MIT
// Actual generated 227 cleanup block with modeled ownership and hardware.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_rom_spi.h"
#include "nes_rom_verify.h"
#include "nes_mcu_loader.h"
typedef struct {int unused;} FIL;
struct sd_report {struct nes_mcu_load_report load;struct nes_verify_report verify;bool verified;};
struct hw_spi {uint32_t SR;};static struct hw_spi hw;static struct hw_spi *SPI1=&hw;
struct diagnostic {unsigned error;};static struct diagnostic diagnostic;
#define SPI_SR_BSY 1u
#define SPI_SR_TXE 2u
#define FR_OK 0
#define FPGA_TEST_TOKEN 0xa5
#define FPGA_BASE "base"
#define NES_DIAG_BLOCKED 1
#define NES_DIAG_RECOVER 2
#define OTG_FS_IRQn 67
static bool failed,return_failed,gpio_owned,query_ok,stop_command_ok,base_ok,configured_ok,token_ok;
static bool close_ok,pending,irq_enabled;static unsigned stop_count,base_count,close_count;
static bool nes_cf86_monitoring094(void){return true;}
static bool nes_cf86_check094(void){return !failed;}
static bool nes_cf86_failed094(void){return failed;}
static bool nes_return_failed(void){return return_failed;}
static bool nes_cf86_fail094(void){failed=true;return false;}
static bool nes_menu_base_only116(void){return false;}
static unsigned f_close(FIL *f){(void)f;close_count++;return close_ok?FR_OK:1;}
static bool sd_query(const struct nes_rom_spi_io *io,struct nes_rom_spi_status *s){(void)io;s->flags=0;s->count=12;return query_ok;}
static bool sd_command(const struct nes_rom_spi_io *io,uint8_t command,uint32_t at,uint8_t arg,struct nes_rom_spi_status *s){
 (void)io;(void)arg;(void)s;assert(command==NES_ROM_STOP&&at==12);stop_count++;return stop_command_ok;
}
static void cf86_end094(void){gpio_owned=false;}
static bool nes_cf86_finish094(void){return !failed;}
static bool nes_diag_sd_failed(void){return false;}
static void nes_diag_progress(int a,uint32_t b,uint32_t c){(void)a;(void)b;(void)c;}
static bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;return true;}
static bool nes_diag_fpga_pgm(const uint8_t *p){(void)p;base_count++;return base_ok;}
static struct diagnostic *nes_diag_status(void){return &diagnostic;}
static bool configured(const char *p){(void)p;return configured_ok;}
static uint8_t fpga_test(void){return token_ok?FPGA_TEST_TOKEN:0;}
static bool nes_menu_diagnostic_pending(void){return pending;}
static void nes_diag_leave(void){}
static void NVIC_EnableIRQ(int irq){assert(irq==OTG_FS_IRQn);irq_enabled=true;}
#include "cleanup407.inc"
static void fresh(void){
 failed=return_failed=irq_enabled=false;gpio_owned=query_ok=stop_command_ok=base_ok=configured_ok=token_ok=close_ok=true;
 pending=false;stop_count=base_count=close_count=0;hw.SR=SPI_SR_TXE;
}
int main(void){
 struct sd_report report;
 fresh();memset(&report,0,sizeof(report));report.verified=true;report.load.stop_ok=true;
 assert(test_cleanup407(&report,true,true,true,true));
 assert(report.load.base_restored&&report.load.recovery_attempted&&base_count==1&&stop_count==0&&irq_enabled);
 fresh();memset(&report,0,sizeof(report));report.verified=true;
 assert(test_cleanup407(&report,true,true,true,true));
 assert(report.load.stop_ok&&stop_count==1&&report.load.base_restored&&base_count==1);
 fresh();memset(&report,0,sizeof(report));report.verified=true;stop_command_ok=false;
 assert(!test_cleanup407(&report,true,true,true,true)&&failed&&!report.verified&&base_count==0&&!irq_enabled);
 fresh();memset(&report,0,sizeof(report));report.verified=true;report.load.result=NES_MCU_LOAD_CHANGED;
 assert(!test_cleanup407(&report,true,true,true,true)&&failed&&!report.verified&&base_count==0&&!irq_enabled);
 fresh();memset(&report,0,sizeof(report));report.verified=true;report.load.stop_ok=true;base_ok=false;
 assert(!test_cleanup407(&report,true,true,true,true)&&failed&&!report.verified&&base_count==1&&!irq_enabled);
 fresh();memset(&report,0,sizeof(report));report.verified=true;report.load.stop_ok=true;token_ok=false;
 assert(!test_cleanup407(&report,true,true,true,true)&&failed&&!report.verified&&base_count==1&&!irq_enabled);
 puts("NROM407 227 cleanup block PASS modeled STOP/base happy and fail-closed cases; no physical IO proof");
 return 0;
}
