/* SPDX-License-Identifier: MIT */
/* Production single-block writer + DATA/CRC/status/busy helper; GPIO modeled. */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "nes_menu_return.h"
typedef uint8_t BYTE;typedef uint32_t DWORD;typedef unsigned UINT;
typedef enum {RES_OK,RES_ERROR,RES_WRPRT,RES_NOTRDY,RES_PARERR} DRESULT;
enum {DISK_OK,DISK_ERROR};enum {TRANS_NONE,TRANS_READ};
static unsigned disk_state,ccs,card,wp,sd_offload,ff_sd_offload,during_blocktrans,mode,commands,sends,rx_cycle;
static uint8_t rsp[6],payload[512];static uint32_t addresses[4];static uint16_t observed_crc[4];
static unsigned lane_bits[4],out_count;static bool nes_diag_sd_fault;
static void nes_diag_sd_error(enum nes_diag_error e){nes_diag_sd_fault=true;nes_diag_fail(e);}
bool nes_diag_sd_failed(void){return nes_diag_sd_fault;}
uint32_t nes_diag_ticks(void){return 0;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
static uint8_t crc7update(uint8_t c,uint8_t d){for(unsigned i=0;i<8;i++){c<<=1;if(d&128)c^=128;if(c&128)c^=9;d<<=1;}return c;}
static uint16_t crc_xmodem_update(uint16_t c,uint8_t d){c^=(uint16_t)d<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));return c;}
static bool nes_diag_sd_response(unsigned command){uint8_t c=0;for(unsigned i=0;i<5;i++)c=crc7update(c,rsp[i]);return rsp[0]==command&&rsp[5]==(uint8_t)((c<<1)|1)&&!(rsp[1]|rsp[2]|rsp[3]|rsp[4]);}
static int cmd_fast(unsigned command,uint32_t address,unsigned crc,uint8_t *data,uint8_t *reply){(void)crc;assert(command==24&&!data);addresses[commands++]=address;memset(reply,0,6);reply[0]=24;uint8_t c=0;for(unsigned i=0;i<5;i++)c=crc7update(c,reply[i]);reply[5]=(uint8_t)((c<<1)|1);if(mode==1)return 0;if(mode==2)reply[5]^=2;return 6;}
#define MAX_CARDS 1
#define WRITE_BLOCK 24
#define SDCARD_DETECT card
#define SDCARD_WP wp
#define DBG_SD if(0)
#define SD_DAT0REG 0
#define SD_DAT1REG 0
#define SD_DAT2REG 0
#define SD_DAT3REG 0
#define SD_DAT0BIT 0
#define SD_DAT1BIT 1
#define SD_DAT2BIT 2
#define SD_DAT3BIT 3
#define GPIO_MODE_OUT(r,p) ((void)0)
#define GPIO_MODE_IN(r,p) do{if((p)==0){sends++;rx_cycle=0;}}while(0)
static void output(unsigned n){if(out_count>=1&&out_count<=1024){unsigned i=out_count-1;assert(n==((payload[i/2]>>((i&1)?0:4))&15));}out_count++;}
#define SD_DAT_OUT(n) output(n)
#define OUT_BIT(r,p,n) (lane_bits[p]=(n))
static void wiggle_fast_pos1(void){if(out_count==1025)for(unsigned i=0;i<4;i++)observed_crc[i]=(uint16_t)((observed_crc[i]<<1)|lane_bits[i]);}
static void wiggle_fast_neg1(void){rx_cycle++;}
static void wiggle_fast_neg(unsigned n){rx_cycle+=n;}
static unsigned input(void){if(rx_cycle>=3&&rx_cycle<7){unsigned status=mode==3?5:mode==4?10:2;return (status>>(6-rx_cycle))&1;}return mode==5?0:1;}
#define BITBAND(r,p) input()
#include "sd-write-functions.inc"
#include "nes_return_sd_write.inc"
static void setup(unsigned m){mode=m;disk_state=DISK_OK;ccs=card=1;wp=sd_offload=ff_sd_offload=during_blocktrans=commands=sends=rx_cycle=out_count=0;memset(observed_crc,0,sizeof(observed_crc));nes_diag_sd_fault=false;nes_return_reset();nes_diag_begin();nes_return_log_allow(true);}
int main(void){setvbuf(stdout,0,_IONBF,0);unsigned cases=0;uint8_t data[1024];
 for(unsigned i=0;i<512;i++)data[i]=payload[i]=(uint8_t)(i*73+19);memcpy(data+512,data,512);
 setup(0);assert(nes_return_sd_write(0,data,7,1)==RES_OK&&commands==1&&sends==1&&addresses[0]==7);cases++;
 for(unsigned lane=0;lane<4;lane++){uint16_t crc=0;for(unsigned n=0;n<1024;n++){unsigned b=(payload[n/2]>>((n&1)?lane:lane+4))&1;unsigned feedback=(crc>>15)^b;crc=(uint16_t)((crc<<1)^(feedback?0x1021:0));}assert(observed_crc[lane]==crc);}
 setup(0);ccs=0;assert(nes_return_sd_write(0,data,7,1)==RES_OK&&addresses[0]==3584);cases++;
 for(unsigned m=1;m<=5;m++){printf("SD_WRITE fault=%u\n",m);setup(m);assert(nes_return_sd_write(0,data,7,2)==RES_ERROR&&commands==1&&nes_diag_sd_fault);assert(nes_return_sd_write(0,data,7,1)==RES_NOTRDY&&commands==1);cases++;}
 setup(0);nes_return_log_allow(false);assert(nes_return_sd_write(0,data,7,1)==RES_WRPRT&&!commands&&!nes_diag_sd_fault);cases++;
 setup(0);wp=1;assert(nes_return_sd_write(0,data,7,1)==RES_WRPRT&&!commands);cases++;
 setup(0);card=0;assert(nes_return_sd_write(0,data,7,1)==RES_NOTRDY&&!commands);cases++;
 for(unsigned n=0;n<3;n++){setup(0);if(n==0)sd_offload=1;if(n==1)ff_sd_offload=1;if(n==2)during_blocktrans=TRANS_READ;assert(nes_return_sd_write(0,data,7,1)==RES_ERROR&&!commands);cases++;}
 setup(0);assert(nes_return_sd_write(0,data,UINT32_MAX,2)==RES_PARERR&&!commands);cases++;
 setup(0);ccs=0;assert(nes_return_sd_write(0,data,0x800000,1)==RES_PARERR&&!commands);cases++;
 setup(0);nes_return_fail(NES_DIAG_SPI);assert(nes_return_sd_write(0,data,7,1)==RES_NOTRDY&&!commands);cases++;
 printf("PASS MENU065 SD_write cases=%u all4_crc=1 no_retry=1 busy_frozen_tick=1\n",cases);return 0;
}
