/* SPDX-License-Identifier: MIT */
/* Full062 menu call, compact lossless SPI transaction capture. Each GPIO
 * transition/sample is checked against the actual2us C transfer template. */
#include "session-platform.c"
static void full_session(const char *fixture,const char *trace_path,unsigned chr32) {
 FILE *input=fopen(fixture,"rb");assert(input);
 original_length=(unsigned)fread(rom,1,sizeof(rom),input);fclose(input);
 assert(original_length==(chr32?98320u:81936u));
 initialize(NONE,1);wave_path=0;session_trace=fopen(trace_path,"w");assert(session_trace);
 trace_ss=!!(mock_a.ODR&16);trace_sck=!!(mock_b.ODR&8);trace_frames=trace_bits=trace_samples=0;
 assert(nes_menu_diagnostic_run((const uint8_t *)(chr32?"NES VERIFY 062 96.nh1":"NES VERIFY 062 80.nh1")));
 assert(begin_count==1&&end_count==1&&finishes==1&&stop_count==1&&configs==2&&irq==1&&reset_held);
 assert(check_reads==original_length-16&&check_acks==check_reads&&closes==2&&!count&&!flags);
 assert(trace_frames==5u*(original_length-16u)+16u);
 fclose(session_trace);session_trace=0;
 assert(nes_menu_diagnostic_prepared(true));reset_held=0;nes_menu_diagnostic_released();
 assert(strstr(last_log,"verified=1")&&strstr(last_log,"stop_ok=1")&&strstr(last_log,"base_restored=1"));
 printf("PASS SESSION C bytes=%u frames=%u delay_ns=%llu compared=%u no_START=1\n",
  original_length-16,trace_frames,ns,check_acks);
}
int main(int argc,char **argv) {
 setvbuf(stdout,0,_IONBF,0);assert(argc==5);
 full_session(argv[1],argv[3],0);full_session(argv[2],argv[4],1);
 return 0;
}
