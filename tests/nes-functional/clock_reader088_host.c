/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#include "nes_clock_reader088.h"
#include "nes_menu_return.h"
struct gpio088 gpio_b,gpio_ss;struct spi088 spi;struct nvic088 nvic;
int sd_offload,ff_sd_offload,during_blocktrans;
static unsigned checks,delays,reads,frames,fail_check,fail_delay,mode,flip_byte,flip_mask;
static unsigned bit_no,byte_no,shift,command,ss,sck,mosi,rxbit;
static uint8_t packet[16];static uint64_t time_us;static uint32_t origin;
static bool held,failed,freeze_tick,reset_lost,usb_lost,done_lost,reentry;
static FILE *wave;static unsigned tests;
static void trace(unsigned event,unsigned value) {if(wave)fprintf(wave,"%llu %u %u\n",(unsigned long long)(time_us*1000),event,value);}
static void le(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(i*8));}
static void capture(void) {
 memset(packet,0,16);uint32_t seq=(uint32_t)(time_us/1000000);
 if(mode==7)seq+=2;
 if(mode==3)seq=2; /* stopped window counter, readable SPI */
 uint32_t count=seq?1250000:0;uint8_t flags=(uint8_t)(6|(seq?1:0)|(seq==1?8:0));
 if(mode==1){count=0;flags=(uint8_t)(4|(seq?9:0));}
 if(mode==2&&seq){flags|=8;}
 packet[0]=0x87;packet[1]=flags;le(packet+2,seq);le(packet+6,count);le(packet+10,8000000);packet[14]=16;
 if(mode==4)packet[0]=0x86;
 if(mode==7&&frames==2)packet[6]^=1;
 if(mode==5 && frames==2)packet[flip_byte]^=(uint8_t)flip_mask;
 if(mode==6 && seq>=2){le(packet+2,1);}
}
void model_set(struct gpio088 *r,unsigned pin,unsigned value) {
 if(failed)assert((r==&gpio_ss&&pin==0&&value)||(r==&gpio_b&&pin==3&&!value));
 if(value)r->ODR|=1u<<pin;else r->ODR&=~(1u<<pin);
 if(r==&gpio_ss) {
  assert(pin==0);trace(0,value);
  if(ss&&!value){bit_no=byte_no=shift=command=0;frames++;}
  ss=value;return;
 }
 assert(r==&gpio_b&&(pin==3||pin==5));
 if(pin==5){mosi=value;trace(2,value);return;}
 trace(1,value);
 if(!ss&&!sck&&value) {
  uint8_t response=byte_no==0?0:command==0xcf?0x87:command==0xc0&&byte_no<=16?packet[byte_no-1]:0;
  rxbit=(response>>(7-bit_no))&1u;
  shift=(shift<<1)|mosi;
  if(++bit_no==8){bit_no=0;if(byte_no==0){command=shift&255;if(command==0xc0)capture();}byte_no++;shift=0;}
 }
 sck=value;
}
unsigned model_input(void){assert(!failed&&!ss&&sck);reads++;trace(3,rxbit);return rxbit;}
int get_snes_reset(void){return held&&!reset_lost;}
void snes_reset(int n){assert(n==1);held=true;}
int fpga_get_done(void){return !done_lost;}
bool nes_diag_active(void){return true;}
bool nes_return_failed(void){return failed;}
bool nes_return_log_allowed(void){return false;}
void nes_return_fail(enum nes_diag_error e){(void)e;failed=true;}
uint32_t nes_diag_ticks(void){return origin+(freeze_tick?0:(uint32_t)(time_us/10000));}
bool nes_return_io_step(void) {
 assert(!failed);checks++;
 if(reentry){reentry=false;struct clock_report088 nested;assert(!nes_clock_collect088(&nested));return false;}
 if(fail_check&&checks==fail_check){failed=true;return false;}
 if(usb_lost&&checks==100)nvic.ISER[OTG_FS_IRQn>>5]=1u<<(OTG_FS_IRQn&31);
 return true;
}
bool nes_return_delay(unsigned n,bool ms) {
 assert(!ms&&!failed);delays++;
 if(fail_delay&&delays==fail_delay){failed=true;return false;}
 time_us+=n;return true;
}
static void reset(unsigned kind) {
 memset(&gpio_b,0,sizeof(gpio_b));memset(&gpio_ss,0,sizeof(gpio_ss));memset(&nvic,0,sizeof(nvic));
 gpio_b.MODER=0xa5a5a5a5;spi.CR1=0x345;spi.SR=SPI_SR_TXE;gpio_b.ODR=0;
 sd_offload=ff_sd_offload=during_blocktrans=0;
 time_us=0;origin=0;checks=delays=reads=frames=fail_check=fail_delay=0;
 mode=kind;ss=1;sck=mosi=0;held=true;failed=freeze_tick=reset_lost=usb_lost=done_lost=reentry=false;
}
static void outcome(bool ok,enum clock_result088 result) {
 struct clock_report088 report;bool got=nes_clock_collect088(&report);
 if(got!=ok||report.result!=result)fprintf(stderr,"case=%u mode=%u check=%u delay=%u byte=%u mask=%u got=%u result=%u want=%u/%u frames=%u t=%llu\n",tests,mode,fail_check,fail_delay,flip_byte,flip_mask,got,report.result,ok,result,frames,(unsigned long long)time_us);
 assert(got==ok);assert(report.result==result);assert(ss&&!sck&&held);
 if(ok){assert(!failed&&gpio_b.MODER==0xa5a5a5a5&&spi.CR1==0x345);}
 else {assert(failed);}
 tests++;
}
int main(int argc,char **argv) {
 bool absent_trace=argc==3&&!strcmp(argv[2],"absent");
 reset(absent_trace?1:0);if(argc>=2){wave=fopen(argv[1],"w");assert(wave);}
 outcome(true,absent_trace?CLOCK088_ABSENT:CLOCK088_ACTIVE);unsigned normal_checks=checks,normal_frames=frames;
 if(wave){fclose(wave);wave=0;}
 reset(1);outcome(true,CLOCK088_ABSENT);
 reset(2);outcome(true,CLOCK088_UNSTABLE);
 reset(3);outcome(true,CLOCK088_NO_PROGRESS);assert(time_us>=4500000&&time_us<4520000);
 reset(3);freeze_tick=true;outcome(true,CLOCK088_NO_PROGRESS);assert(frames==1025&&time_us<6000000);
 reset(0);origin=0xffffff00u;outcome(true,CLOCK088_ACTIVE);
 reset(4);outcome(false,CLOCK088_PROTOCOL_ERROR);
 reset(7);outcome(false,CLOCK088_PROTOCOL_ERROR);
 /* A single corrupted byte in the first C0 cannot be accepted as a snapshot. */
 for(unsigned byte=0;byte<16;byte++)if(byte!=1)for(unsigned bit=0;bit<8;bit++) {
  reset(5);flip_byte=byte;flip_mask=1u<<bit;outcome(false,CLOCK088_PROTOCOL_ERROR);
 }
 for(unsigned n=1;n<=330;n++){reset(0);fail_delay=n;outcome(false,CLOCK088_IO_ERROR);}
 for(unsigned n=1;n<=1500;n++){reset(0);fail_check=n;outcome(false,CLOCK088_IO_ERROR);}
 reset(0);reset_lost=true;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 reset(0);done_lost=true;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 reset(0);usb_lost=true;outcome(false,CLOCK088_IO_ERROR);
 reset(0);sd_offload=1;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 reset(0);during_blocktrans=1;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 reset(0);reentry=true;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 reset(0);spi.SR|=SPI_SR_BSY;outcome(false,CLOCK088_IO_ERROR);assert(frames==0&&delays==1000);
 reset(0);spi.SR=0;outcome(false,CLOCK088_IO_ERROR);assert(frames==0);
 printf("PASS CLOCK_READER088 tests=%u normal_checks=%u normal_frames=%u\n",tests,normal_checks,normal_frames);
 return 0;
}
