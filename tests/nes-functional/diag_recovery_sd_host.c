/* SPDX-License-Identifier: MIT */
/* Production command/CRC/wait/read functions are extracted verbatim from
 * the materialized pinned platform. GPIO/SD card/tick are host models. */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "nes_diag_runtime.h"
typedef uint8_t BYTE;
typedef uint32_t DWORD;
typedef unsigned UINT;
typedef enum {RES_OK,RES_ERROR,RES_WRPRT,RES_NOTRDY,RES_PARERR} DRESULT;
enum {DISK_CHANGED,DISK_REMOVED,DISK_OK,DISK_ERROR};
enum {TRANS_NONE,TRANS_READ,TRANS_WRITE,TRANS_MID};
enum {CMD_RSP,CMD_RSPDAT,CMD_DAT};
#define READ_SINGLE_BLOCK 17
#define STOP_TRANSMISSION 12
#define MAX_CARDS 1
#define CRC_ERROR -1
#define DBG_SD if(0)
#define DBG_SD_OFFLOAD if(0)
static unsigned disk_state,ccs=1,card=1,cycle,receiving;
static int sd_offload,ff_sd_offload,sd_offload_partial,sd_offload_tgt;
static unsigned sd_offload_partial_start,sd_offload_partial_end,during_blocktrans,last_offset;
static uint8_t rsp[17],wire_response[6];
static bool nes_diag_sd_fault;
static void nes_diag_sd_error(enum nes_diag_error);
static uint32_t ticks,tick_step;
static unsigned commands,legacy_reads,clock_count;
static unsigned mode,stub_fault;
static uint8_t payload[512];static uint16_t lane_crc[4];
enum {GOOD,NO_RESPONSE,NO_DATA,BUSY,CRC_BAD,EARLY};
enum {STUB_OK,STUB_TIMEOUT,STUB_BADCRC,STUB_WRONGCMD,STUB_STATUS,STUB_DATACRC,STUB_STOP};
uint32_t nes_diag_ticks(void){ticks+=tick_step;return ticks;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
static uint8_t crc7update(uint8_t crc,uint8_t data){for(unsigned n=0;n<8;n++){crc<<=1;if(data&0x80)crc^=0x80;if(crc&0x80)crc^=9;data<<=1;}return crc;}
static uint16_t crc_xmodem_update(uint16_t crc,uint8_t data){crc^=(uint16_t)data<<8;for(unsigned n=0;n<8;n++)crc=(uint16_t)((crc<<1)^((crc&0x8000)?0x1021:0));return crc;}
static void response(unsigned command){memset(wire_response,0,6);wire_response[0]=command;wire_response[3]=9;uint8_t c=0;for(unsigned n=0;n<5;n++)c=crc7update(c,wire_response[n]);wire_response[5]=(uint8_t)((c<<1)|1);}
static unsigned bit(unsigned pin){
 if(pin==0)return mode==NO_RESPONSE||!receiving||cycle>=48?1:(wire_response[cycle/8]>>(7-cycle%8))&1;
 if(mode==BUSY)return 0;
 if(mode==NO_DATA)return 1;
 return cycle<(mode==EARLY?12u:52u);
}
#define SD_CMDREG 0
#define SD_DAT0REG 0
#define SD_CMDBIT 0
#define SD_DAT0BIT 1
/* The first argument is discarded, so the production GPIO register token
 * remains unchanged in extracted functions. */
#define BITBAND(reg,pin) bit(pin)
#define GPIO_MODE_OUT(reg,pin) ((void)0)
#define GPIO_MODE_IN(reg,pin) do{receiving=1;cycle=0;}while(0)
#define SET_BIT(reg,pin) ((void)0)
#define CLEAR_BIT(reg,pin) ((void)0)
#define SDCARD_DETECT card
static unsigned data_nibble(void){
 unsigned start=(mode==EARLY?13u:53u);if(cycle<start)return 0;
 unsigned index=cycle-start,nibble=0;
 if(index<1024)nibble=(payload[index/2]>>((index&1)?0:4))&15u;
 else if(index<1040)for(unsigned lane=0;lane<4;lane++)nibble|=((lane_crc[lane]>>(15u-(index-1024u)))&1u)<<lane;
 if(mode==CRC_BAD&&index==1024)nibble^=1;
 return nibble;
}
#define SD_DAT_IN data_nibble()
static void wiggle_fast_neg1(void){cycle++;clock_count++;}
static void wiggle_fast_pos1(void){clock_count++;}
static void wiggle_fast_neg(unsigned n){while(n--)wiggle_fast_neg1();}
static void wiggle_fast_pos(unsigned n){clock_count+=n;}
static void fpga_set_sddma_range(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static void fpga_sddma(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
#include "sd-command-functions.inc"
static int cmd_fast(uint8_t command,uint32_t address,uint8_t crc,uint8_t *data,uint8_t *reply){
 (void)address;(void)crc;commands++;response(command);memcpy(reply,wire_response,6);
 if(stub_fault==STUB_TIMEOUT||((stub_fault==STUB_STOP)&&command==12))return 0;
 if(stub_fault==STUB_BADCRC)reply[5]^=2;
 if(stub_fault==STUB_WRONGCMD)reply[0]^=1;
 if(stub_fault==STUB_STATUS){reply[1]=0x80;uint8_t c=0;for(unsigned n=0;n<5;n++)c=crc7update(c,reply[n]);reply[5]=(uint8_t)((c<<1)|1);}
 if(stub_fault==STUB_DATACRC)return CRC_ERROR;
 if(data)memset(data,0x34,512);
 return 6;
}
#include "nes_diag_sd.inc"
static void read_block(DWORD sector,BYTE *data){(void)sector;(void)data;legacy_reads++;}
static void readled(unsigned n){(void)n;}
#include "sd-read-function.inc"
static void setup(void){
 ticks=cycle=clock_count=commands=receiving=legacy_reads=0;mode=GOOD;stub_fault=0;card=1;disk_state=DISK_OK;ccs=1;sd_offload=ff_sd_offload=sd_offload_partial=0;during_blocktrans=TRANS_NONE;tick_step=0;
 memset(lane_crc,0,sizeof(lane_crc));
 for(unsigned n=0;n<512;n++)payload[n]=(uint8_t)(n*73u+19u);
 for(unsigned n=0;n<1024;n++)for(unsigned lane=0;lane<4;lane++){
  unsigned value=(payload[n/2]>>(((n&1)?0:4)+lane))&1u;
  unsigned feedback=(lane_crc[lane]>>15)^value;
  lane_crc[lane]=(uint16_t)((lane_crc[lane]<<1)^(feedback?0x1021:0));
 }
 nes_diag_sd_reset();nes_diag_begin();
}
int main(void){
 unsigned cases=0;uint8_t data[1024],command[6]={0x51,0,0,0,0,0};
 uint8_t known[5]={0x40,0,0,0,0};uint8_t c=0;for(unsigned n=0;n<5;n++)c=crc7update(c,known[n]);assert(((c<<1)|1)==0x95);
 setup();assert(sdn_read(0,data,2,2)==RES_OK&&commands==2&&data[0]==0x34&&data[1023]==0x34&&!legacy_reads);cases++;
 setup();during_blocktrans=TRANS_MID;assert(sdn_read(0,data,1,1)==RES_OK&&commands==2&&during_blocktrans==TRANS_NONE);cases++;
 setup();sd_offload_partial=1;assert(sdn_read(0,data,1,1)==RES_OK);cases++;
 for(unsigned n=STUB_TIMEOUT;n<=STUB_DATACRC;n++){
  printf("SD stub=%u\n",n);fflush(stdout);
  setup();stub_fault=n;assert(sdn_read(0,data,1,2)==RES_ERROR&&commands==1&&nes_diag_sd_fault&&!legacy_reads);
  assert(sdn_read(0,data,1,1)==RES_NOTRDY&&commands==1);cases++;
 }
 setup();stub_fault=STUB_STOP;during_blocktrans=TRANS_READ;assert(sdn_read(0,data,1,1)==RES_ERROR&&commands==1);cases++;
 for(unsigned n=0;n<4;n++){setup();if(n==0)sd_offload=1;if(n==1)ff_sd_offload=1;if(n==2)card=0;if(n==3)disk_state=DISK_CHANGED;assert(sdn_read(0,data,1,1)!=RES_OK&&!commands);cases++;}
 setup();assert(sdn_read(1,data,1,1)==RES_PARERR&&sdn_read(0,0,1,1)==RES_PARERR&&sdn_read(0,data,1,0)==RES_PARERR&&sdn_read(0,data,1,129)==RES_PARERR&&sdn_read(0,data,UINT32_MAX,2)==RES_PARERR&&!commands);cases++;
 setup();ccs=0;assert(sdn_read(0,data,0x800000,1)==RES_PARERR&&!commands);cases++;
 setup();nes_diag_leave();assert(sdn_read(0,data,1,1)==RES_OK&&legacy_reads==1&&!commands);cases++;
 setup();mode=BUSY;tick_step=1;wait_busy();assert(nes_diag_sd_fault&&nes_diag_status()->error==NES_DIAG_SD_BUSY&&clock_count<102);cases++;
 setup();mode=BUSY;wait_busy();assert(nes_diag_sd_fault&&clock_count==2000000u);cases++;
 setup();mode=NO_RESPONSE;assert(send_command_fast(command,rsp,data)==0&&nes_diag_status()->error==NES_DIAG_SD_RESPONSE);cases++;
 setup();mode=NO_DATA;response(17);assert(send_command_fast(command,rsp,data)==0&&nes_diag_status()->error==NES_DIAG_SD_DATA);cases++;
 setup();mode=GOOD;response(17);memset(data,0xff,512);assert(send_command_fast(command,rsp,data)==6&&!nes_diag_sd_fault&&!memcmp(data,payload,512));cases++;
 setup();mode=CRC_BAD;response(17);assert(send_command_fast(command,rsp,data)==CRC_ERROR&&nes_diag_status()->error==NES_DIAG_SD_CRC);cases++;
 setup();mode=EARLY;response(17);assert(send_command_fast(command,rsp,data)==6&&!nes_diag_sd_fault&&!memcmp(data,payload,512));cases++;
 setup();mode=BUSY;tick_step=1;command[0]=0x4c;response(12);assert(send_command_fast(command,rsp,0)==0&&nes_diag_status()->error==NES_DIAG_SD_BUSY);cases++;
 printf("PASS RECOVERY064 SD cases=%u native_command=6 sticky_error=1 no_retry=1\n",cases);return 0;
}
