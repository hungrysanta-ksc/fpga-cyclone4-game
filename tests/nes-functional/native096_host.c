/* SPDX-License-Identifier: MIT */
#include "platform.c"
#include "native096_bridge.h"
#include "rle.h"
#include "diskio.h"
#include <signal.h>
static unsigned scenario096,poll096,config_bytes096,config_tail096,config_mask096,first_error096;
static unsigned long long native_ns096;
static unsigned first_commands096,first_frames096,first_configs096,first_bytes096,tick_origin096;
static unsigned delayed_ready096,ready_start_poll096,recovery_budget096;
static unsigned measured096,first_edges096;
static unsigned gbc_spi_pacing;
FIL file_handle;
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
 unsigned at=config_bytes096;uint8_t expected=at==0?0x9b:at<4?0xa1:at<262?0xb2:(uint8_t)((at-253)%64);
 assert(b==expected);config_bytes096++;native_ns096+=scenario096==1007?25000000u:1000u;
}
static void tail096(void){config_tail096++;if(config_tail096==3&&scenario096!=1004&&!(scenario096==1008&&configs==2))done=1;}
static void fpga_postinit(void){assert(config_bytes096==1353&&config_tail096==3);mock_a.IDR|=32;mock_spi.SR=SPI_SR_TXE;ready_start_poll096=poll096;if(scenario096==1005||scenario096==1010||(scenario096==1012&&configs==1))mock_a.IDR&=~32u;if(scenario096==1006)mock_spi.SR=0;if(scenario096==1009&&configs==2)mock_spi.SR=SPI_SR_BSY;}
#define FPGA_DIN_MASK() (config_mask096=1)
#define FPGA_DIN_UNMASK() (config_mask096=0)
#define FPGA_SEND_BYTE_SERIAL(b) send_config096(b)
#define CCLK() tail096()
#include "config.inc"
#include "ready.inc"
uint16_t sram_writeblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint16_t sram_readblock(void*p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
int main(int argc,char **argv){
 signal(SIGABRT,failed096);assert(argc==5);setvbuf(stdout,0,_IONBF,0);
 FILE *f=fopen(argv[1],"rb");assert(f);original_length=(unsigned)fread(rom,1,sizeof(rom),f);fclose(f);
 scenario096=(unsigned)strtoul(argv[2],0,10);initialize(NONE,1);mock_a.IDR=32;
 card_profile096((unsigned)strtoul(argv[4],0,10));card_setup096(rom,original_length);native_ns096=ns=0;poll096=0;measured096=1;
 if(scenario096==1011)tick_origin096=UINT32_MAX-5;
 if(scenario096&&scenario096<1000)card_phase_fault096(scenario096/100,scenario096%100,(unsigned)strtoul(argv[3],0,10));
 struct nes_menu_probe_report r;bool safe=nes_menu_sd_probe(original_length==98320?"/sd2snes/nes/banks32.nes":"/sd2snes/nes/fine_x.nes","/sd2snes/fpga_n86.bi3",original_length==98320,&r);
 printf("RESULT096 safe=%u verified=%u failed=%u commands=%u frames=%u config=%u bytes=%u error=%u\n",safe,r.sd.verified,nes_cf86_failed094(),card_commands096(),frames,configs,r.sd.verify.compared,nes_diag_status()->error);
 assert(!card_writes096());
 if(!scenario096||scenario096==1011||scenario096==1012){assert(safe&&r.sd.verified&&r.sd.load.stop_ok&&r.sd.load.base_restored&&configs==2&&irq&&reset_held&&finishes==1&&check_acks==original_length-16);assert(!memcmp(loaded,rom+16,original_length-16));card_summary096();}
 else {
  assert(!safe&&!r.sd.verified&&nes_cf86_failed094()&&!irq&&reset_held&&first_error096);
  assert(card_commands096()==first_commands096&&frames==first_frames096&&configs==first_configs096&&config_bytes096==first_bytes096);
  assert(card_edges096()==first_edges096&&nes_diag_status()->error==first_error096);
  if(scenario096==1010)assert(poll096-ready_start_poll096>=1000000u&&poll096-ready_start_poll096<1000020u);
  unsigned edges=card_edges096();uint8_t scratch[512];assert(disk_read(0,scratch,0,1)!=RES_OK&&disk_write(0,scratch,0,1)!=RES_OK&&card_edges096()==edges);
  unsigned before_commands=card_commands096(),before_frames=frames,before_configs=configs;
  mock_a.IDR|=32;done=1;nes_return_reset();nes_diag_begin();
  assert(!nes_menu_sd_probe("/sd2snes/nes/fine_x.nes","/sd2snes/fpga_n86.bi3",false,&r));
  assert(card_commands096()==before_commands&&frames==before_frames&&configs==before_configs&&!irq&&reset_held);
 }
 printf("PASS096 bytes=%u commands=%u frames=%u configs=%u scenario=%u ticks=%u\n",original_length-16,card_commands096(),frames,configs,scenario096,nes_diag_ticks());return 0;
}
