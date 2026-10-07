/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <crtdbg.h>
#include "nes_diag_runtime.h"
_Static_assert(sizeof(DWORD)==4,"Windows DWORD matches 32-bit FatFS sector");
typedef enum {RES_OK,RES_ERROR,RES_WRPRT,RES_NOTRDY,RES_PARERR} DRESULT;
enum {CLK,CMD,DAT0,DAT1,DAT2,DAT3};enum {CMD_RSP,CMD_RSPDAT,CMD_DAT,TRANS_NONE,TRANS_MID,DISK_OK,CRC_ERROR=-1};
static unsigned level,rises,receiving,falls,cmd_end,data_end,data_mask,data_value,samples,commands;
static unsigned busy_length,status_token,end_bit,bad_rsp,card=1,wp,disk_state=DISK_OK,ccs=1;
static uint8_t rsp[17],wire[6],payload[512];static uint16_t crc_seen[4],crc_expected[4];
static bool nes_diag_sd_fault;static uint32_t ticks,tick_step;
static int sd_offload,ff_sd_offload,sd_offload_partial,sd_offload_tgt;
static unsigned sd_offload_partial_start,sd_offload_partial_end,during_blocktrans,last_offset;
uint32_t nes_diag_ticks(void){ticks+=tick_step;return ticks;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){(void)r;(void)active;}
static void nes_diag_sd_error(enum nes_diag_error n){nes_diag_sd_fault=true;nes_diag_fail(n);}
static bool nes_return_failed(void){return nes_diag_sd_fault;}
static bool nes_return_log_allowed(void){return true;}
static void fpga_set_sddma_range(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static void fpga_sddma(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static int get_and_check_datacrc(uint8_t *p){(void)p;assert(0);return 0;}
/* Host replacements for unchanged ARM assembly CRC primitives. The lane
 * monitor below independently consumes serial bits rather than packed bytes. */
static uint8_t crc7update(uint8_t c,uint8_t d){for(unsigned i=0;i<8;i++){c<<=1;if(d&128)c^=128;if(c&128)c^=9;d<<=1;}return c;}
static uint16_t crc_xmodem_update(uint16_t c,uint8_t d){c^=(uint16_t)d<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));return c;}
static void set_pin(unsigned pin,unsigned value){
 if(pin==CMD)return;
 if(pin>=DAT0){data_value=(data_value&~(1u<<(pin-DAT0)))|(value<<(pin-DAT0));return;}
 assert(pin==CLK);
 if(level&&!value&&receiving)falls++;
 if(!level&&value){
  rises++;if(receiving&&falls==49)cmd_end=rises;
  if(data_mask==15){
   unsigned n=samples++;
   if(n==0)assert(data_value==0&&rises-cmd_end==2);
   else if(n<=1024){unsigned at=n-1;assert(data_value==((payload[at/2]>>((at&1)?0:4))&15));for(unsigned lane=0;lane<4;lane++){unsigned fb=(crc_expected[lane]>>15)^((data_value>>lane)&1);crc_expected[lane]=(uint16_t)((crc_expected[lane]<<1)^(fb?0x1021:0));}}
   else if(n<=1040)for(unsigned lane=0;lane<4;lane++)crc_seen[lane]=(uint16_t)((crc_seen[lane]<<1)|((data_value>>lane)&1));
   else {assert(n==1041&&data_value==15);for(unsigned lane=0;lane<4;lane++)assert(crc_seen[lane]==crc_expected[lane]);data_end=rises;}
  }
 }
 level=value;
}
static unsigned input(unsigned pin){
 if(pin==CMD){if(!receiving||falls<2||falls>=50)return 1;unsigned n=falls-2;return(wire[n/8]>>(7-n%8))&1;}
 assert(pin==DAT0&&data_mask==0&&data_end&&level==1);
 unsigned n=rises-data_end;
 if(n>=3&&n<=6)return(status_token>>(6-n))&1;
 if(n==7)return end_bit;
 if(n>=8&&n-8<busy_length)return 0;
 return 1;
}
static void mode_in(unsigned pin){if(pin==CMD){receiving=1;falls=0;commands++;}else data_mask&=~(1u<<(pin-DAT0));}
static void mode_out(unsigned pin){if(pin==CMD)receiving=0;else data_mask|=1u<<(pin-DAT0);}
#define SD_CLKREG 0
#define SD_CLKBIT CLK
#define SD_CMDREG 0
#define SD_CMDBIT CMD
#define SD_DAT0REG 0
#define SD_DAT0BIT DAT0
#define SD_DAT1REG 0
#define SD_DAT1BIT DAT1
#define SD_DAT2REG 0
#define SD_DAT2BIT DAT2
#define SD_DAT3REG 0
#define SD_DAT3BIT DAT3
#define SET_BIT(r,p) set_pin(p,1)
#define CLEAR_BIT(r,p) set_pin(p,0)
#define BITBAND(r,p) input(p)
#define GPIO_MODE_IN(r,p) mode_in(p)
#define GPIO_MODE_OUT(r,p) mode_out(p)
#define SD_DAT_IN 15
#define SD_DAT_OUT(n) (data_value=(n))
#define OUT_BIT(r,p,n) set_pin(p,n)
#define __DSB() ((void)0)
#define __NOP() ((void)0)
#define DBG_SD if(0)
#define DBG_SD_OFFLOAD if(0)
#define MAX_CARDS 1
#define SDCARD_DETECT card
#define SDCARD_WP wp
#include "functions.inc"
static void setup(unsigned busy,unsigned token,unsigned end,unsigned bad){
 level=rises=receiving=falls=cmd_end=data_end=data_mask=data_value=samples=commands=0;
 memset(crc_seen,0,sizeof(crc_seen));memset(crc_expected,0,sizeof(crc_expected));ticks=tick_step=0;nes_diag_sd_fault=false;
 busy_length=busy;status_token=token;end_bit=end;bad_rsp=bad;during_blocktrans=TRANS_NONE;nes_diag_begin();
 memset(wire,0,sizeof(wire));wire[0]=24;wire[3]=9;uint8_t c=0;for(unsigned i=0;i<5;i++)c=crc7update(c,wire[i]);wire[5]=(uint8_t)((c<<1)|1);if(bad_rsp)wire[5]^=2;
}
int main(void){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);setvbuf(stdout,0,_IONBF,0);
 unsigned checks=0;const unsigned busy[]={0,1,2,3,32,2048};
 for(unsigned pattern=0;pattern<4;pattern++){
  for(unsigned i=0;i<512;i++)payload[i]=pattern==0?0:pattern==1?255:pattern==2?(uint8_t)i:(uint8_t)(i*73+19);
  for(unsigned j=0;j<6;j++){
   setup(busy[j],2,1,0);assert(nes_return_sd_write(0,payload,7,1)==RES_OK&&!nes_diag_sd_fault&&samples==1042&&commands==1);
   unsigned tail=rises-(data_end+7);if(CANDIDATE)assert(tail>=8);else if(j<3)assert(tail<8);
   printf("WRITE077 pattern=%u busy=%u after_status_end=%u candidate=%u\n",pattern,busy[j],tail,CANDIDATE);checks++;
  }
 }
 setup(0,2,0,0);DRESULT r=nes_return_sd_write(0,payload,7,1);
 printf("END077 corrupted_end_result=%u candidate=%u\n",r,CANDIDATE);
 assert(CANDIDATE?(r==RES_ERROR&&nes_diag_status()->error==NES_DIAG_SD_RESPONSE):(r==RES_OK));checks++;
 for(unsigned token=0;token<16;token++)if(token!=2){
  setup(0,token,1,0);assert(nes_return_sd_write(0,payload,7,1)==RES_ERROR&&nes_diag_sd_fault);
  unsigned old=rises;assert(nes_return_sd_write(0,payload,7,1)==RES_NOTRDY&&rises==old&&commands==1);checks++;
 }
 setup(0,2,1,1);assert(nes_return_sd_write(0,payload,7,1)==RES_ERROR&&nes_diag_sd_fault&&!samples);checks++;
 setup(UINT32_MAX,2,1,0);assert(nes_return_sd_write(0,payload,7,1)==RES_ERROR&&nes_diag_status()->error==NES_DIAG_SD_BUSY);assert(rises-data_end<2000100);checks++;
 setup(UINT32_MAX,2,1,0);ticks=UINT32_MAX-40;tick_step=1;assert(nes_return_sd_write(0,payload,7,1)==RES_ERROR&&nes_diag_status()->error==NES_DIAG_SD_BUSY&&rises-data_end<110);checks++;
 printf("PASS077 checks=%u all4_lanes=1 frozen_tick=1 wrap=1 no_retry=1 physical=0\n",checks);return 0;
}
