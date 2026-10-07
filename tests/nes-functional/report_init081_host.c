/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual081 initializer + frozen080 runtime; GPIO card/time/CRC modeled. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
#include "diskio.h"
#include "ff.h"
#include "nes_menu_return.h"
enum {CLK,CMD,DAT0,DAT3};
enum {TRANS_NONE,TRANS_READ};
#define MAX_CARDS 1
#define GO_IDLE_STATE 0
#define SEND_IF_COND 8
#define SD_SEND_OP_COND 41
#define SELECT_CARD 7
#define ALL_SEND_CID 2
#define SEND_RELATIVE_ADDR 3
#define SEND_CSD 9
#define SEND_CID 10
#define SEND_STATUS 13
#define SD_SET_BUS_WIDTH 6
#define SET_BLOCKLEN 16
#define SD_CLKREG (&gpio)
#define SD_CMDREG (&gpio)
#define SD_DAT0REG (&gpio)
#define SD_DAT3REG (&gpio)
#define SD_CLKBIT CLK
#define SD_CMDBIT CMD
#define SD_DAT0BIT DAT0
#define SD_DAT3BIT DAT3
#define SDCARD_DETECT card
#define SDCARD_WP wp
#define SET_BIT(r,p) set_pin(p,1)
#define CLEAR_BIT(r,p) set_pin(p,0)
#define GPIO_MODE_OUT(r,p) mode_pin(p,1)
#define GPIO_MODE_IN(r,p) mode_pin(p,0)
#define BITBAND(r,p) read_pin(p)
#define DBG_SD if(0)
struct fake_nvic nvic;
static bool nes_diag_sd_fault;
static unsigned card,wp,held,clk,cmdlevel,cmdout,cmdclocks,command,commands;
static unsigned response_pos,response_len,busy_clocks,attempts,high_capacity,cmd_bits,assigned;
static unsigned delays,fail_delay,remove_delay,tick_div,tick_origin,io_at_fault;
static unsigned corrupt_at,corrupt_kind,timeout_at,never_ready,never_unbusy,checks;
static unsigned log_commands[5000],log_count;
static uint8_t wire[6],response[17],csd[17],cid[17],ccs;
static uint32_t rca;
static diskinfo0_t di;
volatile enum diskstates disk_state;
int sd_offload,ff_sd_offload,during_blocktrans;
int sd_offload_partial;
uint16_t sd_offload_partial_start,sd_offload_partial_end;
static unsigned ios;
static uint8_t crc7update(uint8_t c,uint8_t d){for(unsigned i=0;i<8;i++){c<<=1;if(d&128)c^=128;if(c&128)c^=9;d<<=1;}return c;}
/* Independent bit polynomial for model responses and outgoing command check. */
static uint8_t model_crc(const uint8_t *p,unsigned n){
 unsigned r=0;for(unsigned i=0;i<n*8;i++){
  unsigned feedback=((r>>6)^((p[i/8]>>(7-i%8))&1))&1;
  r=((r<<1)&127)^(feedback?9:0);
 }return (uint8_t)((r<<1)|1);
}
uint32_t nes_diag_ticks(void){return tick_origin+(tick_div?delays/tick_div:0);}
void nes_diag_observe(const struct nes_diag_report *r,bool active){if(active&&r->error&&!io_at_fault)io_at_fault=ios;}
uint8_t get_snes_reset(void){return (uint8_t)held;}
bool nes_return_delay(unsigned n,bool ms){
 assert(n==2&&!ms&&!nes_return_failed());delays++;
 if(delays==remove_delay)card=0;
 if(delays==fail_delay){nes_return_fail(NES_DIAG_TIMER);return false;}
 return true;
}
static void set_bits(uint8_t *r,unsigned first,unsigned bits,uint32_t value){
 for(unsigned i=0;i<bits;i++)if(value&(1u<<(bits-1-i)))r[(first+i)/8]|=0x80u>>((first+i)%8);
}
static void respond(void){
 assert(cmd_bits==48&&wire[5]==model_crc(wire,5));
 command=wire[0]&63;commands++;assert(log_count<5000);log_commands[log_count++]=command;
 uint32_t arg=((uint32_t)wire[1]<<24)|((uint32_t)wire[2]<<16)|((uint32_t)wire[3]<<8)|wire[4];
 memset(response,0,sizeof(response));response_pos=0;response_len=6;response[0]=(uint8_t)command;
 switch(command){
 case 0:assert(arg==0);response_len=0;break;
 case 8:assert(arg==0x1aa);response[3]=1;response[4]=0xaa;break;
 case 55:assert(arg==(assigned?0x12340000u:0));response[4]=0x20;break;
 case 41:
  assert(arg==0x40fc0000u);attempts++;response[0]=0x3f;response[1]=(attempts>=3&&!never_ready?0x80:0)|(high_capacity?0x40:0);response[2]=0xfc;break;
 case 2:assert(!arg);response_len=17;response[0]=0x3f;response[1]=3;response[9]=0x67;break;
 case 3:assert(!arg);assigned=1;response[1]=0x12;response[2]=0x34;response[3]=7;break;
 case 9:
  assert(arg==0x12340000u);response_len=17;response[0]=0x3f;
  if(high_capacity){set_bits(response,8,2,1);set_bits(response,66,22,4095);}
  else{set_bits(response,52,4,9);set_bits(response,62,12,4095);set_bits(response,86,3,7);}
  break;
 case 7:assert(!arg||arg==0x12340000u);if(!arg)response_len=0;else busy_clocks=3;break;
 case 13:assert(arg==0x12340000u);response[3]=9;break;
 case 6:assert(arg==2);response[3]=9;break;
 case 16:assert(arg==512);response[3]=9;break;
 default:assert(0);
 }
 if(commands==corrupt_at){
  if(corrupt_kind==3)response[0]^=1;
  if(corrupt_kind==4){
   if(command==8)response[4]^=1;
   else if(command==41)response[2]=0;
   else if(command==3)response[3]|=0x80;
   else if(command==9)response[1]^=0x80;
   else if(command==55)response[4]=0;
   else if(command==13)response[3]=7;
   else response[1]|=0x80;
  }
 }
 if(response_len){
  unsigned first=response_len==17?1:0,last=response_len-1;
  response[last]=command==41?255:model_crc(response+first,last-first);
  if(commands==corrupt_at){if(corrupt_kind==1)response[last]^=2;if(corrupt_kind==2)response[last]&=254;}
 }
}
static void set_pin(unsigned pin,unsigned value){
 assert(!nes_return_failed());ios++;
 if(pin==CMD){cmdlevel=value;return;}
 if(pin==DAT3)return;
 assert(pin==CLK);
 if(!clk&&value){
  if(cmdout){
   if(cmd_bits<48&&(cmd_bits||!cmdlevel)){wire[cmd_bits/8]=(uint8_t)((wire[cmd_bits/8]<<1)|cmdlevel);cmd_bits++;}
   cmdclocks++;
  }else {response_pos++;if(busy_clocks&&response_pos>response_len*8+8)busy_clocks--;}
 }
 clk=value;
}
static void mode_pin(unsigned pin,unsigned output){
 assert(!nes_return_failed());ios++;
 if(pin==DAT3)return;
 assert(pin==CMD);cmdout=output;
 if(output){cmdclocks=cmd_bits=0;memset(wire,0,6);}else respond();
}
static unsigned read_pin(unsigned pin){
 assert(!nes_return_failed());
 if(pin==DAT0)return !(busy_clocks||never_unbusy);
 if(pin==DAT3)return 1;
 assert(pin==CMD);
 if(commands==timeout_at||response_pos>=response_len*8)return 1;
 return (response[response_pos/8]>>(7-response_pos%8))&1;
}
/* Actual legacy initializer is included to prove it still refuses active
 * diagnostics before its unbounded slow transport/UART can be reached. */
static int cmd_slow(unsigned a,uint32_t b,unsigned c,void *d,uint8_t *r){(void)a;(void)b;(void)c;(void)d;(void)r;assert(0);return 0;}
static int acmd_slow(unsigned a,uint32_t b,unsigned c,void *d,uint8_t *r){return cmd_slow(a,b,c,d,r);}
static void wiggle_slow_neg(unsigned n){(void)n;assert(0);}
static void uart_trace(void *p,unsigned a,unsigned b){(void)p;(void)a;(void)b;assert(0);}
static DRESULT sdn_getinfo(BYTE a,BYTE b,void *p){(void)a;(void)b;(void)p;assert(0);return RES_ERROR;}
#include "native.inc"
#include "nes_report_init081.inc"
static unsigned mount_reads,mount_error;
DSTATUS disk_status(BYTE d){return sdn_status(d);}
DRESULT disk_read(BYTE d,BYTE *p,DWORD sector,UINT count){
 assert(!d&&!sector&&count==1&&disk_state==DISK_OK&&!nes_return_failed());mount_reads++;
 if(mount_error){nes_diag_sd_error(NES_DIAG_SD_CRC);return RES_ERROR;}
 /* Minimal FAT16 VBR. Data transfer is explicitly modeled in this mount test. */
 memset(p,0,512);p[0]=0xeb;p[1]=0x3c;p[2]=0x90;p[12]=2;p[13]=1;p[14]=1;
 p[16]=2;p[18]=2;p[20]=32;p[21]=0xf8;p[22]=32;
 memcpy(p+54,"FAT16   ",8);p[510]=0x55;p[511]=0xaa;return RES_OK;
}
DRESULT disk_write(BYTE d,const BYTE *p,DWORD s,UINT n){(void)d;(void)p;(void)s;(void)n;assert(0);return RES_ERROR;}
DRESULT disk_ioctl(BYTE d,BYTE c,void *p){(void)d;(void)c;(void)p;assert(0);return RES_ERROR;}
DWORD get_fattime(void){assert(0);return 0;}
static void mount_tests(void){
 FATFS fs={0};
 assert(f_mount(&fs,"/",1)==FR_OK&&fs.fs_type==FS_FAT16&&mount_reads==1);checks++;
 unsigned before=commands;
 assert(f_mount(NULL,"/",0)==FR_OK&&f_mount(&fs,"/",1)==FR_OK&&commands==before&&mount_reads==2);checks++;
 mount_error=1;assert(f_mount(NULL,"/",0)==FR_OK&&f_mount(&fs,"/",1)==FR_DISK_ERR&&nes_return_failed());checks++;
 unsigned reads=mount_reads;
 assert(f_mount(&fs,"/",1)==FR_NOT_READY&&mount_reads==reads&&commands==before);checks++;
 assert(f_mount(NULL,"/",0)==FR_OK);
}
static void reset(void){
 nes_diag_leave();nes_diag_sd_reset();nes_return_reset();
 card=held=1;wp=clk=cmdlevel=cmdout=cmdclocks=commands=response_pos=response_len=busy_clocks=attempts=0;
 delays=fail_delay=remove_delay=tick_div=tick_origin=io_at_fault=corrupt_at=corrupt_kind=timeout_at=never_ready=never_unbusy=ios=log_count=0;
 sd_offload=ff_sd_offload=during_blocktrans=0;memset(&nvic,0,sizeof(nvic));
 disk_state=DISK_CHANGED;report_init081_used=false;high_capacity=1;rca=0;ccs=0;assigned=0;memset(csd,0xcc,17);memset(cid,0xcc,17);
 nes_diag_begin();nes_return_io_begin();
}
static void failed(void){
 assert(nes_return_failed()&&disk_state!=DISK_OK&&held&&rca==0&&csd[0]==0xcc&&cid[0]==0xcc);
 unsigned before=ios;enum nes_diag_error first=nes_diag_status()->error;
 assert(!sdn_report_initialize081()&&ios==before&&nes_diag_status()->error==first);checks++;
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,0,_IONBF,0);
 const unsigned expected[]={7,0,8,55,41,55,41,55,41,2,3,9,7,13,55,6,16};
 reset();bool ok=sdn_report_initialize081();
 if(!ok)printf("initial failure error=%u command=%u count=%u delays=%u responsepos=%u\n",nes_diag_status()->error,command,commands,delays,response_pos);
 assert(ok);
 assert(log_count==sizeof(expected)/sizeof(*expected)&&!memcmp(log_commands,expected,sizeof(expected)));
 assert(disk_state==DISK_OK&&ccs==1&&rca==0x12340000u&&di.sectorcount==4194304&&di.sectorsize==2&&cid[9]==0x67);
 unsigned total_delays=delays,total_commands=commands;checks++;
 unsigned before=ios;assert(!sdn_report_initialize081()&&ios==before);checks++;
 reset();high_capacity=0;assert(sdn_report_initialize081()&&!ccs&&di.sectorcount==2097152);checks++;
 reset();tick_origin=UINT32_MAX-1;tick_div=2000;nes_return_io_begin();assert(sdn_report_initialize081());checks++;
 for(unsigned n=1;n<=total_delays;n++){
  reset();fail_delay=n;assert(!sdn_report_initialize081()&&delays==n&&nes_diag_status()->error==NES_DIAG_TIMER);failed();
 }
 for(unsigned n=1;n<=total_delays;n+=17){
  reset();remove_delay=n;assert(!sdn_report_initialize081()&&delays==n);failed();
 }
 for(unsigned n=3;n<=total_commands;n++){
  reset();timeout_at=n;assert(!sdn_report_initialize081()&&commands==n);failed();
  for(unsigned k=1;k<=3;k++){
   reset();corrupt_at=n;corrupt_kind=k;assert(!sdn_report_initialize081()&&commands==n);failed();
  }
  if(expected[n-1]!=2){reset();corrupt_at=n;corrupt_kind=4;assert(!sdn_report_initialize081()&&commands==n);failed();}
 }
 reset();never_ready=1;assert(!sdn_report_initialize081()&&commands<4200);failed();
 reset();never_ready=1;tick_div=3000;assert(!sdn_report_initialize081()&&nes_diag_status()->error==NES_DIAG_SD_BUSY&&attempts<2048);failed();
 reset();never_unbusy=1;assert(!sdn_report_initialize081());failed();
 for(unsigned n=0;n<7;n++){
  reset();if(n==0)card=0;if(n==1)sd_offload=1;if(n==2)ff_sd_offload=1;if(n==3)during_blocktrans=1;
  if(n==4)nvic.ISER[2]=8;
  if(n==5)nes_return_log_allow(true);
  if(n==6)nes_diag_leave();
  assert(!sdn_report_initialize081()&&!ios);failed();
 }
 reset();held=0;assert(!sdn_report_initialize081()&&!ios);checks++;
 reset();nes_return_fail(NES_DIAG_SPI);assert(!sdn_report_initialize081()&&!ios&&nes_diag_status()->error==NES_DIAG_SPI);checks++;
 reset();assert(sdn_initialize(0)==STA_NOINIT&&!ios&&nes_diag_sd_failed());checks++;
 reset();assert(disk_initialize(0)&STA_NOINIT);assert(!ios);checks++;
 reset();assert(sdn_report_initialize081());before=ios;assert(disk_initialize(1)&STA_NOINIT);assert(ios==before);checks++;
 reset();assert(sdn_report_initialize081());before=ios;wp=1;assert(disk_initialize(0)==STA_PROTECT&&ios==before);checks++;
 reset();assert(sdn_report_initialize081());mount_tests();
 printf("PASS081 checks=%u delays=%u commands=%u physical=0\n",checks,total_delays,total_commands);return 0;
}
