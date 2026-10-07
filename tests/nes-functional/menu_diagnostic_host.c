/* SPDX-License-Identifier: MIT */
/* Reuse the frozen060 SD/PSRAM mock with062 candidate-aware adaptation.
 * This executes actual menu lifecycle C, not a duplicate menu model. */
#include "sd-platform.c"
int main(int argc,char **argv) {
 assert(sd_regression(argc,argv)==0);
 wave_path=0;
 const uint8_t *small=(const uint8_t *)"/diag/NES VERIFY 062 80.nh1";
 const uint8_t *large=(const uint8_t *)"C:\\diag\\nes verify 062 96.NH1";
 assert(nes_menu_diagnostic_marker(small)&&nes_menu_diagnostic_marker(large));
 const char *bad[]={"","NES H1 044.nh1","NES VERIFY 062 8.nh1","NES VERIFY 062 80.nh1x",
  "xNES VERIFY 062 80.nh1","NES VERIFY 062 80.nes","NES VERIFY 062 96.nh1/other"};
 assert(!nes_menu_diagnostic_marker(0));
 for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++)assert(!nes_menu_diagnostic_marker((const uint8_t *)bad[i]));
 assert(!nes_menu_diagnostic_run(0)&&nes_menu_diagnostic_prepared(false));
 nes_menu_diagnostic_released();assert(!log_attempts);
 unsigned sessions=0;
 for(unsigned scenario=0;scenario<16;scenario++) {
  unsigned which=scenario&1u;
  FILE *input=fopen(argv[which+1],"rb");assert(input);original_length=(unsigned)fread(rom,1,sizeof(rom),input);fclose(input);
  enum fault f=scenario==5?ID:scenario==6?SPI_ID:scenario==7?STOP_FAILED:scenario==13?OPEN:scenario==15?BASE_TOKEN:NONE;
  bool rejected=scenario==5||scenario==6||(scenario>=8&&scenario<=14);
  unsigned enabled=scenario==2?0:1;
  initialize(f,enabled);log_fault=scenario<5?scenario:0;log_attempts=log_closes=0;last_log[0]=0;
  identity_fault=scenario>=8&&scenario<=12?scenario-7:0;
  unsigned selected=which^(scenario==14);
  bool safe=nes_menu_diagnostic_run(selected?large:small);sessions++;
  assert(safe==(f!=BASE_TOKEN));
  assert(!nes_menu_diagnostic_run(small)); /* pending/reentrant session rejected */
  assert(!log_attempts);nes_menu_diagnostic_released();assert(!log_attempts);
  assert(!nes_menu_diagnostic_prepared(false)&&reset_held&&!log_attempts);
  if(f==BASE_TOKEN) {
   assert(!irq&&!nes_menu_diagnostic_prepared(true)&&reset_held&&!log_attempts);
   nes_menu_diagnostic_released();assert(!log_attempts);continue;
  }
  assert(nes_menu_diagnostic_prepared(true)&&reset_held&&irq==enabled&&log_attempts==1);
  if(log_fault!=1)assert(strstr(last_log,"menu_state=PREPARED_RESET_HELD")&&log_closes==1);
  /* This models only the caller reaching RESET release, not physical SNES. */
  reset_held=0;nes_menu_diagnostic_released();assert(log_attempts==2&&irq==enabled);
  if(log_fault!=1) {
   assert(log_closes==2&&strstr(last_log,"menu_state=RELEASE_BOUNDARY_REACHED"));
   assert(strstr(last_log,"candidate=NES-MENU-DIAGNOSTIC-062")&&strstr(last_log,"start_sent=0"));
   assert(strstr(last_log,configs?"base_restored=1":"base_restored=0")&&strstr(last_log,"safe_to_reload=1"));
   assert(strstr(last_log,rejected?"verified=0":"verified=1"));
   assert(strstr(last_log,selected?"geometry_kib=96":"geometry_kib=80"));
   if(rejected)assert(!begin_count&&!count);
   if(f==ID)assert(strstr(last_log,"board_observed_hex=60")&&begin_count==0);
   if(f==STOP_FAILED)assert(strstr(last_log,"stop_ok=0")&&stop_count==1);
  }
  unsigned attempts=log_attempts;nes_menu_diagnostic_released();assert(log_attempts==attempts);
 }
 assert(sessions==16);
 printf("PASS MENU062 regression=41 input_rejections=18 menu_sessions=%u no_START=1\n",sessions);
 return 0;
}
