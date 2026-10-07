/* SPDX-License-Identifier: GPL-2.0-only */
/* Included by the source-derived078 session harness. SRAM/RESET/TIM2/USB are
 * models. FatFS and native SD remain actual frozen077 C. No rendered pixels. */
#include "config.h"
#include "nes_report_checkpoint079.h"
struct mock_nvic checkpoint_nvic;
int snes_boot_configured;
static unsigned held,display_ticks,display_fault,display_at,display_writes,display_reads;
static unsigned releases,display_waits,deadline_extra,release_fault,hold_fault;
static char screen_line[33];
static void checkpoint_reset(void){
 held=1;snes_boot_configured=1;memset(&checkpoint_nvic,0,sizeof(checkpoint_nvic));
 display_ticks=display_fault=display_at=display_writes=display_reads=0;
 releases=display_waits=deadline_extra=release_fault=hold_fault=0;
}
void snes_reset(int n){
 if(!n){assert(!nes_return_failed()&&held&&nes_return_log_allowed());releases++;}
 held=n?1:release_fault;
}
uint8_t get_snes_reset(void){return (uint8_t)(hold_fault?0:held);}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){
 assert(held&&!nes_return_failed()&&!sd_offload&&!ff_sd_offload&&!during_blocktrans);
 assert(a==0xff1000u+33u*8u&&n==33&&((char *)p)[32]==0);
 display_writes++;memcpy(screen_line,p,33);
 if(display_at==stage&&display_fault==1)nes_return_fail(NES_DIAG_SPI);
 return n;
}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){
 assert(held&&!nes_return_failed()&&a==0xff1000u+33u*8u&&n==33);
 display_reads++;memcpy(p,screen_line,n);
 if(display_at==stage&&display_fault==2)((char *)p)[12]^=1;
 if(display_at==stage&&display_fault==3)nes_return_fail(NES_DIAG_SPI);
 return n;
}
bool nes_return_delay(unsigned ms,bool milliseconds){
 assert(milliseconds&&ms==500&&!nes_return_failed());display_waits++;
 assert(!held||release_fault);
 if(display_at==stage&&display_fault==4){nes_return_fail(NES_DIAG_TIMER);return false;}
 display_ticks+=50+deadline_extra;return true;
}
static void checkpoint_tests(void){
 char text[513],name[16];memset(text,'Q',sizeof(text));
 for(unsigned fat=0;fat<2;fat++)for(unsigned at=2;at<=8;at++)for(unsigned mode=1;mode<=4;mode++){
  reset_case(fat);display_at=at;display_fault=mode;
  int r=sdinv_write_report(text,sizeof(text),name,sizeof(name));
  assert(r==8&&nes_return_failed()&&held&&!nes_return_log_allowed());
  assert(first_fault_stage==at&&display_writes==at-1&&commands==first_fault_command);
  unsigned writes=display_writes,reads=display_reads,edges=rises;
  sdinv_checkpoint079(8);assert(display_writes==writes&&display_reads==reads&&rises==edges&&held);
  checks++;
 }
 for(unsigned n=0;n<8;n++){
  reset_case(0);
  if(n==0)snes_boot_configured=0;
  if(n==1)sd_offload=1;
  if(n==2)ff_sd_offload=1;
  if(n==3)during_blocktrans=TRANS_READ;
  if(n==4)checkpoint_nvic.ISER[OTG_FS_IRQn>>5]=1u<<(OTG_FS_IRQn&31);
  if(n==5)held=0;
  if(n==6)hold_fault=1;
  if(n==7)release_fault=1;
  assert(sdinv_write_report(text,sizeof(text),name,sizeof(name))==8);
  assert(nes_return_failed()&&held&&!commands&&!nes_return_log_allowed());
  assert(display_writes==(n==7));checks++;
 }
 reset_case(0);tick_origin=UINT32_MAX-10;
 assert(sdinv_write_report(text,sizeof(text),name,sizeof(name))==0);
 assert(display_ticks==350&&releases==7&&display_waits==7&&held);checks++;
 /* Time spent rendering is charged against the unchanged total deadline. */
 reset_case(0);deadline_extra=1000;tick_origin=UINT32_MAX-10;
 assert(sdinv_write_report(text,sizeof(text),name,sizeof(name))==8);
 assert(held&&commands==0&&display_writes==1&&nes_return_failed());checks++;
 for(unsigned n=0;n<3;n++){
  reset_case(0);nes_return_log_allow(n!=0);
  sdinv_checkpoint079(n==2?9:2);
  if(n==1){assert(!nes_return_failed());}else{assert(nes_return_failed()&&!display_writes);}
  nes_return_log_allow(false);assert(held);checks++;
 }
}
