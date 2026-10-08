/* SPDX-License-Identifier: MIT */
#include "platform.c"
#include "config097_bridge.h"
#include "rle.h"
#include "diskio.h"
#include <signal.h>
#include "nes_menu076.h"
#include "nes_menu_diagnostic.h"
#include <setjmp.h>
static unsigned scenario096,poll096,config_bytes096,config_tail096,config_mask096,first_error096;
static unsigned long long native_ns096;
static unsigned first_commands096,first_frames096,first_configs096,first_bytes096,tick_origin096;
static unsigned delayed_ready096,ready_start_poll096,recovery_budget096;
static unsigned measured096,first_edges096;
static unsigned gbc_spi_pacing;
uint8_t *diag_packed097,*diag_raw097,*base_packed097,*base_raw097,*menu097;
unsigned diag_size097,diag_raw_size097,base_size097,base_raw_size097,menu_size097;
static uint8_t menu_ram097[65536];static unsigned menu_writes097,menu_reads097,release097,product_commands097;
static snes_romprops_t romprops;
FIL file_handle;
static void file_close(void){file_res=f_close(&file_handle);}
#include "classify.inc"
static uint8_t *read_file097(const char *path,unsigned *size){FILE*f=fopen(path,"rb");assert(f);fseek(f,0,SEEK_END);*size=(unsigned)ftell(f);rewind(f);uint8_t*p=malloc(*size);assert(p&&fread(p,1,*size,f)==*size&&!fclose(f));return p;}

void fpga_pgm(uint8_t *p){(void)p;assert(!"legacy programmer must not execute");}
static void failed096(int sig){(void)sig;_Exit(86);}
void native_edge096(unsigned pin,unsigned value){(void)pin;(void)value;if(measured096)assert(!irq&&reset_held);native_ns096+=125;}
uint32_t clock096(void){return tick_origin096+(uint32_t)((ns+native_ns096)/10000000ull);}
uint32_t nes_diag_ticks(void){poll096++;if(scenario096!=1010)native_ns096+=1000;return clock096();}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 if(active&&scenario096==1013&&r->phase==NES_DIAG_LOAD)card_present096(0);
 if(active&&scenario096==1015&&r->phase==NES_DIAG_CHECK)card_invalidate096();
 if(active&&scenario096==1014&&r->phase==NES_DIAG_RECOVER&&!recovery_budget096){recovery_budget096=1;nes_return_io_begin();native_ns096+=60000000000ull;}
 if(active&&r->error&&!first_error096){first_error096=r->error;first_edges096=card_edges096();first_commands096=card_commands096();first_frames096=frames;first_configs096=configs;first_bytes096=config_bytes096;printf("FIRST096 error=%u commands=%u frames=%u config=%u\n",r->error,card_commands096(),frames,configs);}
}
unsigned input096(unsigned value,unsigned bit){
 if(scenario096==1012&&configs==1&&bit==5&&++delayed_ready096==32){mock_a.IDR|=32;value=mock_a.IDR;}
 return(value>>bit)&1u;
}
static void fpga_init(void){assert(!irq&&reset_held&&!nes_return_failed());configs++;config_bytes096=config_tail096=0;}
static void fpga_set_prog_b(unsigned n){mock_a.IDR=(mock_a.IDR&~64u)|((n||scenario096==1001)?64u:0);if(!n)done=scenario096==1003;}
static int fpga_get_initb(void){return scenario096!=1002;}
static void send_config096(uint8_t b){
 assert(config_mask096&&!irq&&reset_held&&!nes_return_failed());
 unsigned at=config_bytes096;assert(at<(configs==1?diag_raw_size097:base_raw_size097));uint8_t expected=(configs==1?diag_raw097:base_raw097)[at];
 assert(b==expected);config_bytes096++;native_ns096+=scenario096==1007?25000000u:1000u;
}
static void tail096(void){config_tail096++;if(config_tail096==3&&scenario096!=1004&&!(scenario096==1008&&configs==2))done=1;}
static void fpga_postinit(void){assert(config_bytes096==(configs==1?diag_raw_size097:base_raw_size097)&&config_tail096==3);mock_a.IDR|=32;mock_spi.SR=SPI_SR_TXE;ready_start_poll096=poll096;if(scenario096==1005||scenario096==1010||(scenario096==1012&&configs==1))mock_a.IDR&=~32u;if(scenario096==1006)mock_spi.SR=0;if(scenario096==1009&&configs==2)mock_spi.SR=SPI_SR_BSY;}
#define FPGA_DIN_MASK() (config_mask096=1)
#define FPGA_DIN_UNMASK() (config_mask096=0)
#define FPGA_SEND_BYTE_SERIAL(b) send_config096(b)
#define CCLK() tail096()
#include "config.inc"
#include "ready.inc"
uint16_t sram_writeblock(void*p,uint32_t a,uint16_t n){
 assert(!irq&&reset_held&&!nes_return_failed()&&a+n<=sizeof(menu_ram097));menu_writes097++;
 if(scenario096==1103&&menu_writes097==128){nes_return_fail(NES_DIAG_SPI);return 0;}
 memcpy(menu_ram097+a,p,n);return n;
}
uint16_t sram_readblock(void*p,uint32_t a,uint16_t n){
 assert(!irq&&reset_held&&!nes_return_failed()&&a+n<=sizeof(menu_ram097));menu_reads097++;memcpy(p,menu_ram097+a,n);
 if(scenario096==1102&&menu_reads097==128)((uint8_t*)p)[0]^=1;
 if(scenario096==1104&&menu_reads097==256)return n-1;
 return n;
}
static bool menu_flow097(void){
 assert(nes_menu_diagnostic_pending()&&!irq&&reset_held&&!nes_return_failed());
 nes_return_io_begin();card_stage097(6);
 if(scenario096==1105)native_ns096+=60000000000ull;
 file_res=f_open(&file_handle,"/sd2snes/m3nu.bin",FA_READ);
 if(file_res!=FR_OK||!memory_classify097())return false;
 card_stage097(7);
 if(nes_return_copy_menu("/sd2snes/m3nu.bin",0,0)!=65536)return false;
 assert(!memcmp(menu097,menu_ram097,65536));
 card_stage097(8);
 if(scenario096==1106)card_present096(0);
 if(!nes_menu_diagnostic_prepared(scenario096!=1107))return false;
 assert(!nes_return_failed()&&!irq&&reset_held);
 snes_reset(0);release097++;delay_ms(100);
 if(scenario096==1108){nes_return_fail(NES_DIAG_SPI);snes_reset(1);return false;}
 nes_menu_diagnostic_released();assert(!nes_diag_active()&&!nes_menu_diagnostic_pending()&&irq&&!reset_held);
 unsigned writes=card_writes096();assert(writes>0);product_commands097=card_commands096();card_summary096();
 /* Report readback is harness-only, after the production lifecycle ends. */
 measured096=0;char text[640];nes_diag_begin();assert(card_report097(text,sizeof(text))>0);nes_diag_leave();
 assert(strstr(text,"verified=1\n")&&strstr(text,"base_restored=1\n")&&strstr(text,"menu_state=PREPARED_RESET_HELD\n"));
 printf("MENU097 copied=65536 writes=%u report_writes=%u release=%u harness_readback_commands=%u\n",menu_writes097,writes,release097,card_commands096()-product_commands097);return true;
}
int main(int argc,char **argv){
 signal(SIGABRT,failed096);assert(argc==10);setvbuf(stdout,0,_IONBF,0);
 FILE *f=fopen(argv[1],"rb");assert(f);original_length=(unsigned)fread(rom,1,sizeof(rom),f);fclose(f);
 diag_packed097=read_file097(argv[5],&diag_size097);diag_raw097=read_file097(argv[6],&diag_raw_size097);
 base_packed097=read_file097(argv[7],&base_size097);base_raw097=read_file097(argv[8],&base_raw_size097);menu097=read_file097(argv[9],&menu_size097);
 scenario096=(unsigned)strtoul(argv[2],0,10);initialize(NONE,1);mock_a.IDR=32;
 if(scenario096==1101)menu097[100]^=1;
 card_profile096((unsigned)strtoul(argv[4],0,10));card_setup096(rom,original_length);native_ns096=ns=0;poll096=0;measured096=1;
 if(scenario096==1011)tick_origin096=UINT32_MAX-5;
 if(scenario096&&scenario096<1000)card_phase_fault096(scenario096/100,scenario096%100,(unsigned)strtoul(argv[3],0,10));
 bool safe=nes_menu_diagnostic_run((const uint8_t*)(original_length==98320?"NES VERIFY 094 96.nh1":"NES VERIFY 094 80.nh1"));
 if(safe){assert(configs==2&&!irq&&reset_held&&finishes==1&&check_acks==original_length-16&&!memcmp(loaded,rom+16,original_length-16));safe=menu_flow097();}
 printf("RESULT097 safe=%u failed=%u commands=%u frames=%u config=%u error=%u\n",safe,nes_cf86_failed094(),card_commands096(),frames,configs,nes_diag_status()->error);
 if(!scenario096||scenario096==1011||scenario096==1012){assert(safe&&irq&&!reset_held&&release097==1);}
 else {
  assert(!safe&&!irq&&reset_held);
  if(scenario096==1101)assert(menu_writes097==0);
  /* menu_ok=false is a main caller failure, not a shared IO fault. */
  if(scenario096!=1107){assert(first_error096);assert(card_commands096()==first_commands096&&frames==first_frames096&&configs==first_configs096&&config_bytes096==first_bytes096&&card_edges096()==first_edges096);}
  unsigned before_commands=card_commands096(),before_frames=frames,before_configs=configs;
  assert(!nes_menu_diagnostic_run((const uint8_t*)"NES VERIFY 094 80.nh1"));
  assert(card_commands096()==before_commands&&frames==before_frames&&configs==before_configs&&!irq&&reset_held);
 }
 printf("PASS097 bytes=%u commands=%u frames=%u configs=%u scenario=%u ticks=%u\n",original_length-16,card_commands096(),frames,configs,scenario096,nes_diag_ticks());return 0;
}
