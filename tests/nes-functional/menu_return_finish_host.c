/* SPDX-License-Identifier: MIT */
/* Actual extracted main RESET/prepared/settle/released section. */
#define main log_lifecycle_checks
#include "log-host.c"
#undef main
#include <setjmp.h>
static jmp_buf blocked;
static unsigned finish_fault,reliable_calls;
enum cicstates {CIC_OK,CIC_PAIR,CIC_SCIC,CIC_FAIL};
static struct {unsigned pairmode,autoboot_enabled;} STM;
static struct {unsigned vidmode_menu;} CFG;
void nes_diag_blocked(void){longjmp(blocked,1);}
void delay_ms(unsigned ms){assert(ms==100&&!irq&&nes_diag_active()&&!held);if(finish_fault==2)nes_return_fail(NES_DIAG_TIMER);}
static enum cicstates get_cic_state(void){return finish_fault==3?CIC_FAIL:finish_fault==5?CIC_PAIR:finish_fault==6?CIC_SCIC:CIC_OK;}
static bool sram_reliable(void){reliable_calls++;if(finish_fault==4&&reliable_calls==2)nes_return_fail(NES_DIAG_SPI);return finish_fault!=1;}
static void cic_pair(unsigned a,unsigned b){(void)a;(void)b;assert(!irq&&nes_diag_active());}
static unsigned cfg_is_autoboot_enabled(void){return 1;}
static void status_load_to_menu(void){assert(!irq&&nes_diag_active());}
static void cli_entrycheck(void){assert(0);}
static void finish(uint32_t nes_menu_size){
#include "main-finish.inc"
 (void)cmd;(void)btime;(void)filesize;
}
int main(void){volatile unsigned cases=0;
 for(volatile unsigned n=0;n<7;n++)for(volatile unsigned enabled=0;enabled<2;enabled++){
  pending=safe_to_reload=prepared=false;irq=enabled;mode=0;held=opens=writes=closes=0;reliable_calls=0;finish_fault=n;nes_diag_leave();
  assert(nes_menu_diagnostic_run((const uint8_t *)"NES VERIFY 065 80.nh1"));
  if(setjmp(blocked)==0){finish(8192);assert(n==0||n>=5);assert(irq==enabled&&!held&&!pending&&!nes_diag_active()&&opens==1);}
  else {assert(n>=1&&n<=4&&held&&!irq&&pending&&nes_diag_active());assert(opens==(n!=1));}
  cases++;
 }
 printf("PASS MENU065 finish cases=%u actual_main_section=1 post_release_fault_reholds_RESET=1\n",cases);return 0;
}
