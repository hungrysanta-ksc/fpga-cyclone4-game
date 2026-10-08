/* SPDX-License-Identifier: MIT */
/* Includes actual C GPIO/packet/FatFS-call model, not native card execution. */
#include "platform094.c"
#include <signal.h>
static void failed_assert094(int code){(void)code;_Exit(86);}
uint32_t nes_diag_ticks(void){return getticks();}
void nes_diag_sd_reset(void){}
bool nes_diag_sd_failed(void){return false;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){(void)r;(void)active;}
bool nes_return_spi_ready(void){
 assert(configs==1&&!irq&&reset_held&&!frames);
 if(scenario094==100){nes_return_fail(NES_DIAG_SPI);return false;}
 return true; /* Actual bounded lower wait is checked separately in069. */
}
bool nes_diag_fpga_pgm(const uint8_t *p){fpga_pgm((uint8_t*)p);return file_res==FR_OK;}
uint16_t sram_readblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint16_t sram_writeblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}

int main(int argc,char **argv){
 signal(SIGABRT,failed_assert094);assert(argc==3);setvbuf(stdout,0,_IONBF,0);
 FILE *f=fopen(argv[1],"rb");assert(f);original_length=(unsigned)fread(rom,1,sizeof(rom),f);fclose(f);
 scenario094=(unsigned)strtoul(argv[2],0,10);
 enum fault selected=scenario094<100?(enum fault)scenario094:NONE;
 initialize(selected,1);mock_a.IDR=32;
 if(selected==HEADER)rom[6]^=4;
 if(selected==CONTENT)rom[32]^=1;
 if(scenario094==120)identity_fault=3; /* CF44 */
 if(scenario094==121)identity_fault=6; /* CF68 */
 if(scenario094==122)identity_fault=7; /* CF85 */
 if(scenario094==123)identity_fault=8; /* CF87 */
 if(scenario094==124)identity_fault=1; /* Legacy F0 mismatch */
 if(scenario094==125)identity_fault=2; /* Legacy F1 mismatch */
 if(scenario094==126)sd_offload=1;
 if(scenario094==127)nes_return_fail(NES_DIAG_SD_DATA);
 if(scenario094==128)mock_a.IDR=0;
 if(scenario094==129)ff_sd_offload=1;
 if(scenario094==130)during_blocktrans=1;
 if(scenario094==131)nes_return_log_allow(true);
 struct nes_menu_probe_report r;
 bool safe=nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&r);
 if(scenario094==0){
  assert(safe&&!nes_cf86_failed094()&&r.board_id==0x86&&r.sd.verified&&r.sd.load.stop_ok);
  assert(configs==2&&count==0&&finishes==1&&check_acks==original_length-16);
  assert(!memcmp(loaded,rom+16,original_length-16));
  assert(mock_b.MODER==mode_before&&mock_spi.CR1==cr1_before&&irq==1&&reset_held);
 } else if(configs==0&&scenario094<100){
  assert(safe&&!nes_cf86_failed094()&&!r.sd.verified&&irq==1&&reset_held);
 } else {
  assert(!safe&&nes_cf86_failed094()&&!r.sd.verified&&!irq&&reset_held);
  if(configs==1)assert(!r.sd.load.recovery_attempted);
  if(selected==RB_DATA)assert(stop_count==0&&configs==1);
  if(scenario094>=101&&scenario094<=111)assert(injected094);
  if(scenario094>=120&&scenario094<=125)assert(!begin_count&&!count);
  unsigned prior_frames=frames,prior_reads=read_calls,prior_configs=configs,prior_closes=closes;
  mock_a.IDR=32;done=1;irq=0;reset_held=1;sd_offload=ff_sd_offload=during_blocktrans=0;
  /* Simulate PLL/READY returning and even unrelated legacy state reset. The
   * new trust lifetime must remain failed without any SD/SPI/config retry. */
  nes_return_reset();nes_diag_begin();
  assert(!nes_cf86_check094()&&!nes_cf86_finish094());
  struct nes_menu_probe_report again;
  assert(!nes_menu_sd_probe("fixture","approved-test-image",false,&again));
  assert(!nes_menu_diagnostic_run((const uint8_t*)"NES VERIFY 094 80.nh1"));
  assert(frames==prior_frames&&read_calls==prior_reads&&configs==prior_configs&&closes==prior_closes);
  assert(!irq&&reset_held&&nes_cf86_failed094());
 }
 printf("PASS094 scenario=%u bytes=%u frames=%u compared=%u verified=%u poisoned=%u config=%u\n",
  scenario094,original_length-16,frames,r.sd.verify.compared,r.sd.verified,nes_cf86_failed094(),configs);
 return 0;
}
