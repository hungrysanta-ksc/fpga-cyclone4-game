/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#include "nes_menu_return.h"
#include "nes_report_boot080.h"
#include "nes_clock_config089.h"
#include "nes_clock_reader088.h"
#include "clock089_payload.h"
#include "cfgware.h"
#include "snesboot.h"
struct gpio088 gpio_b,gpio_ss;struct spi088 spi;struct nvic088 nvic;
int sd_offload,ff_sd_offload,during_blocktrans,snes_boot_configured;
const uint8_t *fpga_config;uint8_t gbc_spi_pacing;
static unsigned checks,delays,tests,held,prog,target,sent,bitpos,din,extra,postinit;
static unsigned fault_at,status_at,owner_at,pin_fault,delay_fault,mutate_at,reenter_at,byte_us;
static unsigned frames,bit_no,byte_no,shift,command,ss,sck,mosi,rxbit,mode,sram_calls;
static uint64_t time_us,epoch;static uint32_t origin;static bool freeze_tick,freeze_window;
static uint8_t packet[16],golden[510856],mini[153544],rom[65535],screen[24*33];
static struct clock_image089 image;
bool __real_nes_return_io_step(void);
bool __wrap_nes_return_io_step(void) {
 assert(!nes_return_failed());checks++;
 if(checks==fault_at){nes_return_fail(NES_DIAG_MENU);return false;}
 if(checks==reenter_at){reenter_at=0;assert(!nes_clock_config089(&image));return false;}
 return __real_nes_return_io_step();
}
uint32_t nes_diag_ticks(void){return origin+(freeze_tick?0:(uint32_t)(time_us/10000));}
void nes_diag_observe(const struct nes_diag_report *r,bool active){(void)r;(void)active;}
bool nes_diag_sd_failed(void){return false;}
void snes_reset(int n){assert(n==1);held=1;}
uint8_t get_snes_reset(void){return (uint8_t)(held&&!(owner_at&&sent>=owner_at));}
bool nes_return_delay(unsigned n,bool ms) {
 assert(!nes_return_failed());delays++;
 if(delays==delay_fault){nes_return_fail(NES_DIAG_TIMER);return false;}
 time_us+=(uint64_t)n*(ms?1000:1);return true;
}
void fpga_init(void){assert(held&&!nes_return_failed());sent=bitpos=extra=0;}
void fpga_set_prog_b(uint8_t n) {
 if(nes_return_failed())assert(n==0);
 prog=n;
}
void fpga_set_cclk(uint8_t n){assert(n==0);}
unsigned read_prog(void){return pin_fault==1?1:prog;}
int fpga_get_initb(void){
 if(pin_fault==2)return 1;
 if(pin_fault==3)return 0;
 if(status_at&&sent>=status_at)return 0;
 return (int)prog;
}
int fpga_get_done(void){
 if(pin_fault==4)return 1;
 if(pin_fault==5)return 0;
 return target==1?sent==sizeof(mini):sent==sizeof(golden)&&extra>=3;
}
void fpga_postinit(void){assert(!nes_return_failed()&&fpga_get_done());postinit++;epoch=time_us;}
void model_din(unsigned n){assert(!nes_return_failed());din=n&1;}
void model_cclk(void){
 assert(held&&!nes_return_failed());
 unsigned limit=target==1?sizeof(mini):sizeof(golden);const uint8_t *bytes=target==1?mini:golden;
 if(sent==limit){extra++;return;}
 assert(din==((bytes[sent]>>bitpos)&1));
 if(++bitpos==8){bitpos=0;sent++;time_us+=byte_us;}
 if(mutate_at&&sent==mutate_at&&target==2){((uint8_t*)image.rle)[image.size-2]^=1;mutate_at=0;}
}
static void le(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(i*8));}
static void capture(void) {
 memset(packet,0,16);uint32_t seq=freeze_window?0:(uint32_t)((time_us-epoch)/1000000);
 uint32_t count=mode==1?0:seq?1250000:0;
 packet[0]=0x87;packet[1]=(uint8_t)((mode==1?4:6)|(seq?1:0)|((mode==1&&seq)||seq==1?8:0));
 le(packet+2,seq);le(packet+6,count);le(packet+10,8000000);packet[14]=16;
}
void model_set(struct gpio088 *r,unsigned pin,unsigned value){
 if(nes_return_failed())assert((r==&gpio_ss&&pin==0&&value)||(r==&gpio_b&&pin==3&&!value));
 if(value)r->ODR|=1u<<pin;else r->ODR&=~(1u<<pin);
 if(r==&gpio_ss){assert(pin==0);if(ss&&!value){bit_no=byte_no=shift=command=0;frames++;}ss=value;return;}
 assert(r==&gpio_b&&(pin==3||pin==5));
 if(pin==5){mosi=value;return;}
 if(!ss&&!sck&&value){
  uint8_t response=byte_no==0?0:command==0xcf?0x87:command==0xc0&&byte_no<=16?packet[byte_no-1]:0;
  rxbit=(response>>(7-bit_no))&1;shift=(shift<<1)|mosi;
  if(++bit_no==8){bit_no=0;if(!byte_no){command=shift&255;if(command==0xc0)capture();}byte_no++;shift=0;}
 }
 sck=value;
}
unsigned model_input(void){assert(!nes_return_failed()&&!ss&&sck);return rxbit;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){
 assert(!nes_return_failed()&&held&&target==1);sram_calls++;
 if(a>=0xff1000){assert(a+n<=0xff1000+sizeof(screen));memcpy(screen+a-0xff1000,p,n);}
 else{assert(a>=0xc00000&&a+n<=0xc00000+sizeof(rom));memcpy(rom+a-0xc00000,p,n);}
 return n;
}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){
 assert(!nes_return_failed()&&held&&target==1);sram_calls++;
 if(a>=0xff1000)memcpy(p,screen+a-0xff1000,n);else memcpy(p,rom+a-0xc00000,n);
 return n;
}
void set_saveram_mask(uint32_t n){assert(n==0x1fff&&!nes_return_failed());}
void set_rom_mask(uint32_t n){assert(n==0x3fffff&&!nes_return_failed());}
void set_mapper(uint8_t n){assert(n==7&&!nes_return_failed());}
static unsigned decoded;
static bool mini_byte(void *ctx,uint8_t value){(void)ctx;assert(decoded<sizeof(mini));mini[decoded++]=value;return true;}
static void reset(void){
 time_us=epoch=origin=0;freeze_tick=freeze_window=false;
 nes_diag_leave();nes_return_reset();nes_diag_begin();nes_return_io_begin();
 memset(&nvic,0,sizeof(nvic));memset(&gpio_b,0,sizeof(gpio_b));memset(&gpio_ss,0,sizeof(gpio_ss));
 spi.CR1=0x345;spi.SR=SPI_SR_TXE;gpio_b.MODER=0xa5a5a5a5;
 checks=delays=prog=sent=bitpos=extra=postinit=fault_at=status_at=owner_at=pin_fault=delay_fault=mutate_at=reenter_at=0;
 frames=bit_no=byte_no=shift=command=sck=mosi=rxbit=mode=sram_calls=0;ss=held=1;target=2;byte_us=1;
 time_us=epoch=origin=0;freeze_tick=freeze_window=false;
 sd_offload=ff_sd_offload=during_blocktrans=snes_boot_configured=0;
 image=(struct clock_image089){clock089_rle,sizeof(clock089_rle),CLOCK089_RAW_SIZE,CLOCK089_CRC};
}
static void rejected(void){
 assert(!nes_clock_config089(&image)&&nes_return_failed()&&held&&!postinit);
 unsigned old=sent;assert(!nes_clock_config089(&image)&&sent==old);tests++;
}
static void combined(unsigned kind){
 reset();mode=kind;target=1;bool boot_ok=report_boot080();
 if(!boot_ok)printf("BOOT_FAIL checks=%u sent=%u sram=%u error=%u reset=%u time=%llu\n",checks,sent,sram_calls,nes_diag_status()->error,held,(unsigned long long)time_us);
 assert(boot_ok);unsigned before=checks;
 target=2;assert(nes_clock_config089(&image));unsigned config=checks-before;
 if(kind==2)freeze_window=true;
 struct clock_report088 r;assert(nes_clock_collect088(&r));
 assert(r.result==(kind==2?CLOCK088_NO_PROGRESS:kind==1?CLOCK088_ABSENT:CLOCK088_ACTIVE));unsigned collected=checks;
 target=1;assert(report_boot080()&&held&&!nes_return_failed());
 assert(spi.CR1==0x345&&checks<1000000&&sram_calls==1120);
 printf("COMBINED089 mode=%u mini_checks=%u config_checks=%u through_reader=%u total_checks=%u frames=%u time_us=%llu\n",kind,before,config,collected,checks,r.frames,(unsigned long long)time_us);tests++;
}
int main(int argc,char **argv){
 setvbuf(stdout,0,_IONBF,0);
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f&&fread(golden,1,sizeof(golden),f)==sizeof(golden)&&fgetc(f)==EOF);fclose(f);
 assert(report_decode080(cfgware,sizeof(cfgware),sizeof(mini),mini_byte,0));
 reset();assert(nes_clock_config089(&image)&&held&&!nes_return_failed()&&sent==sizeof(golden)&&postinit==1&&spi.CR1==0x345);unsigned all=checks;tests++;
 printf("CONFIG089 checks=%u bytes=%u bit_checks=%u\n",all,sent,sent*8);
 combined(0);combined(1);combined(2);
 reset();image.crc^=1;rejected();assert(!sent&&!prog); /* wrong payload before touching FPGA */
 reset();image.size--;rejected();assert(!sent&&!prog);
 reset();image.raw_size--;rejected();assert(!sent&&!prog);
 for(unsigned n=1;n<=5;n++){reset();pin_fault=n;rejected();}
 for(unsigned n=1;n<=2;n++){reset();delay_fault=n;rejected();}
 const unsigned positions[]={1,2,31,32,33,255,256,257,4095,4096,510855,510856};
 for(unsigned i=0;i<sizeof(positions)/sizeof(positions[0]);i++){
  reset();status_at=positions[i];rejected();assert(sent==positions[i]);
  reset();owner_at=positions[i];rejected();assert(sent==positions[i]);
 }
 for(unsigned n=1;n<=all;n+=127){reset();fault_at=n;rejected();assert(checks==n);}
 reset();fault_at=all;rejected();assert(checks==all);
 for(unsigned n=0;n<6;n++){
  reset();if(n==0)held=0;if(n==1)nvic.ISER[2]=8;if(n==2)sd_offload=1;if(n==3)ff_sd_offload=1;if(n==4)during_blocktrans=1;if(n==5)nes_return_log_allow(true);
  rejected();assert(!sent);
 }
 reset();spi.SR|=SPI_SR_BSY;rejected();assert(!sent);
 reset();spi.SR=0;rejected();assert(!sent);
 reset();reenter_at=2;rejected();assert(!sent);
 reset();origin=0xfffffff0u;nes_return_io_begin();assert(nes_clock_config089(&image));tests++;
 /* Model expensive CPU work: global/local deadline, no budget reinitialization. */
 reset();time_us=60000000;rejected();assert(!sent);
 reset();byte_us=20;rejected();assert(time_us>=5000000&&time_us<5000640&&sent<sizeof(golden));
 /* With frozen ticks and a stopped FPGA window, the unchanged global poll
  * limit may win over reader512queries: shared fault blocks mini/SD return. */
 reset();target=1;assert(report_boot080());target=2;assert(nes_clock_config089(&image));
 origin=(uint32_t)(time_us/10000);freeze_tick=freeze_window=true;
 struct clock_report088 stopped;assert(nes_clock_collect088(&stopped)&&stopped.result==CLOCK088_NO_PROGRESS);
 target=1;assert(!report_boot080()&&nes_return_failed()&&held&&checks==1000001);
 printf("FROZEN089 shared_fault_checks=%u mini_return_bytes=%u no_SD=1\n",checks,sent);tests++;
 printf("PASS CONFIG089 tests=%u config_checks=%u physical=0 linked_firmware=0\n",tests,all);return 0;
}
