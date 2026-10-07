/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>
#ifdef _WIN32
#include <windows.h>
#include <crtdbg.h>
#endif
enum {CLK,CMD,DAT0,DAT1,DAT2,DAT3};
enum {CMD_RSP,CMD_RSPDAT,CMD_DAT,TRANS_MID,CRC_ERROR=-1};
enum {NES_DIAG_SD_RESPONSE,NES_DIAG_SD_DATA,NES_DIAG_SD_CRC};
static unsigned level,rises,receive,falls,delay,end_edge,start_edge,start_pending,cmd_out;
static uint8_t response[6];static jmp_buf stop;
static bool nes_diag_sd_fault;
static int sd_offload,sd_offload_partial,sd_offload_tgt;
static unsigned sd_offload_partial_start,sd_offload_partial_end,during_blocktrans,last_offset;
static int nes_diag_active(void){return 1;}
static void nes_diag_sd_error(unsigned n){(void)n;assert(0);}
static void fpga_set_sddma_range(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static void fpga_sddma(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static int get_and_check_datacrc(uint8_t *p){(void)p;assert(0);return 0;}
static void wait_busy(void){assert(0);}
static uint16_t crc_xmodem_update(uint16_t a,uint8_t b){(void)a;(void)b;assert(0);return 0;}
static void set_pin(unsigned pin,unsigned value){
 if(pin==CMD){cmd_out=value;return;}
 assert(pin==CLK);
 if(level&&!value&&receive)falls++;
 if(!level&&value){
  rises++;
  if(receive&&falls==delay+47)end_edge=rises;
  if(start_pending){start_edge=rises;longjmp(stop,1);}
 }
 level=value;
}
static unsigned input(unsigned pin){
 assert(pin==CMD);
 if(!receive||falls<delay||falls>=delay+48)return 1;
 unsigned n=falls-delay;return(response[n/8]>>(7-n%8))&1;
}
static void mode_in(unsigned pin){assert(pin==CMD);receive=1;falls=0;}
static void mode_out(unsigned pin){if(pin==CMD)receive=0;}
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
#define SD_DAT_OUT(n) do{assert((n)==0);start_pending=1;}while(0)
#define OUT_BIT(r,p,n) do{(void)(p);(void)(n);assert(0);}while(0)
#define __DSB() ((void)0)
#define __NOP() ((void)0)
#define DBG_SD if(0)
#define DBG_SD_OFFLOAD if(0)
#include "functions.inc"
static void run(unsigned command,unsigned gap,unsigned initial,unsigned latency){
 uint8_t cmd[6]={(uint8_t)(0x40|command),0,0,0,0,1},rsp[6]={0},data[512]={0};
 level=initial;rises=receive=falls=end_edge=start_edge=start_pending=cmd_out=0;delay=latency;
 response[0]=(uint8_t)command;response[1]=response[2]=response[3]=response[4]=0;response[5]=1;
 assert(send_command_fast(cmd,rsp,0)==6);
 for(unsigned i=0;i<6;i++)assert(rsp[i]==response[i]);
 assert(end_edge&&level==1&&rises==end_edge+1);
 if(!setjmp(stop)){if(gap)wiggle_fast_pos((uint16_t)gap);send_datablock(data);assert(0);}
 assert(start_edge-end_edge==(gap?10u:2u));
 printf("EDGE075 CMD%u extra=%u initial=%u response_delay=%u end_to_start=%u\n",command,gap,initial,latency,start_edge-end_edge);
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 const unsigned delays[]={1,2,8,64};
 for(unsigned command=24;command<=25;command++)for(unsigned gap=0;gap<=8;gap+=8)for(unsigned initial=0;initial<2;initial++)for(unsigned d=0;d<4;d++)run(command,gap,initial,delays[d]);
 puts("PASS075 edge_cases=32 CMD24_gap2 extra8_gap10 hardware=0");return 0;
}
