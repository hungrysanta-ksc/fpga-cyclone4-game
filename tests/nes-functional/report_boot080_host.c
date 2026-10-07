/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual080 boot/decode/platform +079 runtime. GPIO/SRAM/SD-session models. */
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
#include "config.h"
#include "nes_menu_return.h"
#include "nes_report_boot080.h"
#include "rle.h"
#include "cfgware.h"
#include "snesboot.h"
#include "fileops.h"
struct fake_nvic nvic;
int snes_boot_configured,sd_offload,ff_sd_offload,during_blocktrans;
const uint8_t *fpga_config;
uint8_t gbc_spi_pacing;
int file_res,file_status;
static unsigned checks,held,prog,configured,sent,postinit,io,atfault,atcorrupt;
static unsigned pinfault,delayfault,write_calls,write_result,stage,ticks,clock_step;
static unsigned legacy_pos,legacy_expected_size;
static const uint8_t *legacy_expected;
static uint8_t rom[65535],screen[24*33],golden_mini[153544],golden_boot[65535];
static jmp_buf stopped;
bool report_session080(void);
void snes_reset(int n){if(!n)assert(!nes_return_failed()&&snes_boot_configured);held=(unsigned)n;}
uint8_t get_snes_reset(void){return (uint8_t)held;}
uint32_t nes_diag_ticks(void){ticks+=clock_step;return ticks;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
bool nes_diag_sd_failed(void){return false;}
void nes_diag_sd_reset(void){}
void sdinv_fault_stage(unsigned n){stage=n;}
void nes_diag_blocked(void){assert(held);longjmp(stopped,1);}
void fpga_init(void){assert(held&&!nes_return_failed());}
void fpga_set_prog_b(uint8_t n){prog=n;}
unsigned read_prog(void){return pinfault==1?1:prog;}
int fpga_get_initb(void){return pinfault==2?0:(int)prog;}
int fpga_get_done(void){if(pinfault==3)return 1;if(pinfault==4)return 0;return sent==153544;}
void send_byte(uint8_t n){assert(held&&!nes_return_failed()&&sent<153544&&n==golden_mini[sent]);sent++;}
void fpga_postinit(void){assert(sent==153544);postinit++;configured=1;}
bool nes_return_delay(unsigned t,bool ms){assert(ms&&t==1);if(delayfault){nes_return_fail(NES_DIAG_TIMER);return false;}return true;}
static bool touch(void){assert(held&&configured&&!nes_return_failed());io++;if(io==atfault){nes_return_fail(NES_DIAG_SPI);return false;}return true;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){
 if(!touch())return n;
 if(a>=0xff1000){assert(a+n<=0xff1000+sizeof(screen));memcpy(screen+a-0xff1000,p,n);}
 else{assert(a>=0xc00000&&a+n<=0xc00000+sizeof(rom));memcpy(rom+a-0xc00000,p,n);}
 return n;
}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){
 if(!touch())return n;
 if(a>=0xff1000)memcpy(p,screen+a-0xff1000,n);else memcpy(p,rom+a-0xc00000,n);
 if(io==atcorrupt)((uint8_t *)p)[0]^=1;
 return n;
}
void set_saveram_mask(uint32_t x){assert(x==0x1fff);(void)touch();}
void set_rom_mask(uint32_t x){assert(x==0x3fffff);(void)touch();}
void set_mapper(uint8_t x){assert(x==7);(void)touch();}
uint8_t file_getc(void){assert(0);return 0;}
int sdinv_write_report(const char *p,unsigned n,char *name,size_t size){
 assert(held&&configured&&snes_boot_configured&&!nes_return_failed()&&!nvic.ISER[2]);
 assert(n==3072&&size>=14&&!memcmp(p,"SDREPORT080-NATIVE077",20));
 assert(!memcmp(screen+5*33,"SDREPORT080 STORAGE TEST",23));write_calls++;
 strcpy(name,"/HW080000.TXT");
 if(write_result==8)nes_return_fail(NES_DIAG_SD_BUSY);
 return (int)write_result;
}
static void reset(void){
 nes_diag_leave();nes_return_reset();nes_diag_begin();nes_return_io_begin();
 held=1;prog=configured=sent=postinit=io=atfault=atcorrupt=0;
 pinfault=delayfault=write_calls=write_result=stage=ticks=clock_step=0;
 sd_offload=ff_sd_offload=during_blocktrans=snes_boot_configured=0;
 file_res=0;nvic.ISER[2]=0;memset(rom,0xcc,sizeof(rom));memset(screen,0xcc,sizeof(screen));
}
static bool compare(void *ctx,uint8_t b){(void)ctx;assert(legacy_pos<legacy_expected_size&&b==legacy_expected[legacy_pos]);legacy_pos++;return true;}
static unsigned legacy(const uint8_t *s,unsigned size,uint8_t *out,unsigned limit){
 unsigned n=0;rle_mem_init(s,size);for(;;){uint8_t b=rle_mem_getc();if(rle_state)break;assert(n<limit);out[n++]=b;}return n;
}
static bool reject_sink(void *ctx,uint8_t b){(void)ctx;(void)b;return false;}
static bool run_session(void){nes_diag_leave();return report_session080();}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,0,_IONBF,0);
 assert(legacy(cfgware,sizeof(cfgware),golden_mini,sizeof(golden_mini))==153544);
 assert(legacy(bootrle,sizeof(bootrle),golden_boot,sizeof(golden_boot))==65535);
 legacy_expected=golden_mini;legacy_expected_size=153544;legacy_pos=0;
 assert(report_decode080(cfgware,sizeof(cfgware),153544,compare,0)&&legacy_pos==153544);checks++;
 legacy_expected=golden_boot;legacy_expected_size=65535;legacy_pos=0;
 assert(report_decode080(bootrle,sizeof(bootrle),65535,compare,0)&&legacy_pos==65535);checks++;
 const uint8_t malformed[][5]={{0x9b,255},{0x5b,1,255},{0x77,1,2,255},{0x5b,1,0,255},{1,2,3,4,0}};
 const unsigned lengths[]={2,3,4,4,5};
 for(unsigned i=0;i<5;i++){assert(!report_decode080(malformed[i],lengths[i],1,compare,0));checks++;}
 assert(!report_decode080(cfgware,sizeof(cfgware),1,compare,0));checks++;
 assert(!report_decode080(cfgware,sizeof(cfgware),153544,reject_sink,0));checks++;
 reset();assert(report_boot080()&&held&&postinit==1&&snes_boot_configured);
 assert(!memcmp(rom,golden_boot,sizeof(rom)));unsigned all_io=io;assert(all_io==563);checks++;
 for(unsigned n=1;n<=all_io;n++){
  reset();atfault=n;assert(!report_boot080()&&held&&nes_return_failed()&&!snes_boot_configured&&io==n);
  assert(!report_line080(8,"AFTER FAULT")&&io==n);checks++;
 }
 for(unsigned n=2;n<=512;n+=2){reset();atcorrupt=n;assert(!report_boot080()&&held&&nes_return_failed()&&io==n);checks++;}
 for(unsigned n=517;n<=563;n+=2){reset();atcorrupt=n;assert(!report_boot080()&&held&&nes_return_failed()&&io==n);checks++;}
 for(unsigned n=1;n<=4;n++){reset();pinfault=n;clock_step=1;assert(!report_boot080()&&held&&nes_return_failed());checks++;}
 reset();pinfault=2;assert(!report_boot080()&&held&&nes_return_failed());checks++;
 reset();ticks=UINT32_MAX-10;clock_step=1;pinfault=2;assert(!report_boot080()&&held&&nes_return_failed());checks++;
 reset();delayfault=1;assert(!report_boot080()&&held&&nes_diag_status()->error==NES_DIAG_TIMER);checks++;
 reset();assert(run_session()&&!held&&write_calls==1&&nes_diag_active()&&!nvic.ISER[2]);
 assert(!memcmp(screen+8*33,"TXT SAVED + READBACK OK",22));unsigned total=io;checks++;
 for(unsigned n=all_io+1;n<=total;n++){
  reset();atfault=n;assert(!run_session()&&held&&nes_return_failed()&&io==n);checks++;
 }
 reset();write_result=4;assert(run_session()&&!held&&write_calls==1&&!memcmp(screen+8*33,"TXT SAVE FAILED",15));checks++;
 reset();write_result=8;assert(!run_session()&&held&&nes_return_failed()&&io==all_io+4);checks++;
 reset();file_res=3;assert(!run_session()&&held&&!sent&&!io&&!write_calls&&nes_return_failed());checks++;
 reset();assert(!report_session080()&&held&&!sent&&!io&&nes_return_failed());checks++;
 reset();nes_return_fail(NES_DIAG_SPI);assert(!run_session()&&held&&!sent&&!io&&nes_diag_status()->error==NES_DIAG_SPI);checks++;
 for(unsigned mode=0;mode<5;mode++){
  reset();if(mode==0)sd_offload=1;if(mode==1)ff_sd_offload=1;if(mode==2)during_blocktrans=1;if(mode==3)held=0;if(mode==4)nvic.ISER[2]=8;
  assert(!report_boot080()&&held&&!sent&&!io&&nes_return_failed());checks++;
 }
 printf("PASS080 checks=%u mini153544 boot65535 io%u platform_io%u physical=0\n",checks,all_io,total);return 0;
}
