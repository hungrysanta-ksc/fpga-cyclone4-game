/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual frozen FatFS/report/native C; simulated pre-initialized card/GPIO/
 * clock and host replacements for ARM CRC primitives. No physical evidence. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ff.h"
#include "diskio.h"
#include "nes_menu_return.h"
#include "nes_sd_inventory.h"
#include "nes_sd_inventory_log073.h"

enum {CLK,CMD,DAT0,DAT1,DAT2,DAT3};
enum {CMD_RSP,CMD_RSPDAT,CMD_DAT};
enum {TRANS_NONE,TRANS_READ,TRANS_WRITE,TRANS_MID};
enum {NONE,END_BAD,R1_BAD,READ_CRC_BAD,READ_ALTER,BUSY_FOREVER,R1_TIMEOUT,DATA_TIMEOUT};
#define CRC_ERROR (-1)
#define READ_SINGLE_BLOCK 17
#define STOP_TRANSMISSION 12
static uint8_t media[70000u*512u],write_data[512],read_data[512],cmd_wire[6],response[6],rsp[17];
static FATFS fs;
static unsigned sectors,root_sector,stage,stage_mask,checks;
static unsigned level,rises,falls,receiving,cmd_pending,cmd_value,cmd_bits;
static unsigned cmd_number,cmd_sector,response_rise,read_start,data_end,samples,data_mask,data_value;
static unsigned commands,write_commands,read_commands,commits,read_nibbles,syncs;
static unsigned fault,fault_at,command_fault,busy_clocks,wp,card=1,ccs=1;
static unsigned tick_div,tick_origin,first_fault_stage,first_fault_command,first_fault_rises;
static unsigned command_kind[4096],command_stage[4096];
static uint16_t write_crc[4],write_seen[4],read_crc[4];
static bool nes_diag_sd_fault;
int sd_offload,ff_sd_offload,sd_offload_partial,sd_offload_tgt;
uint16_t sd_offload_partial_start,sd_offload_partial_end;
volatile enum diskstates disk_state;
static int during_blocktrans;
static unsigned last_offset;
static void nes_diag_sd_error(enum nes_diag_error);
static int cmd_fast(uint8_t,uint32_t,uint8_t,uint8_t *,uint8_t *);
static uint8_t crc7update(uint8_t c,uint8_t d){for(unsigned i=0;i<8;i++){c<<=1;if(d&128)c^=128;if(c&128)c^=9;d<<=1;}return c;}
static uint16_t crc_xmodem_update(uint16_t c,uint8_t d){c^=(uint16_t)d<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));return c;}
static void crc_nibble(uint16_t *crc,unsigned data){
 for(unsigned lane=0;lane<4;lane++){unsigned fb=(crc[lane]>>15)^((data>>lane)&1);crc[lane]=(uint16_t)((crc[lane]<<1)^(fb?0x1021:0));}
}
uint32_t nes_diag_ticks(void){return tick_origin+(tick_div?rises/tick_div:0);}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 if(active&&r->error&&!first_fault_stage){first_fault_stage=stage;first_fault_command=commands;first_fault_rises=rises;}
}
void sdinv_fault_stage(unsigned n){assert(n>=2&&n<=8);stage=n;stage_mask|=1u<<n;}
static void fpga_set_sddma_range(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static void fpga_sddma(unsigned a,unsigned b){(void)a;(void)b;assert(0);}
static void readled(int n){(void)n;assert(0);}
static void writeled(int n){(void)n;assert(0);}
static void read_block(uint32_t a,uint8_t *p){(void)a;(void)p;assert(0);}
static void write_block(uint32_t a,uint8_t *p){(void)a;(void)p;assert(0);}
static void flush_write(void){assert(0);}
static unsigned sdn_status(BYTE d){(void)d;assert(0);return 0;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint32_t nes_menu_crc076(uint32_t c,const uint8_t *p,unsigned n){(void)c;(void)p;(void)n;assert(0);return 0;}

/* Card decodes the command pins, not cmd_fast arguments. */
static void start_response(void){
 assert(cmd_bits==48);uint8_t crc=0;
 for(unsigned i=0;i<5;i++)crc=crc7update(crc,cmd_wire[i]);
 assert(cmd_wire[5]==(uint8_t)((crc<<1)|1));
 cmd_number=cmd_wire[0]&63;assert(cmd_number==17||cmd_number==24);
 uint32_t address=((uint32_t)cmd_wire[1]<<24)|((uint32_t)cmd_wire[2]<<16)|((uint32_t)cmd_wire[3]<<8)|cmd_wire[4];
 assert(ccs||!(address&511));cmd_sector=ccs?address:address/512;
 assert(cmd_sector<sectors&&!nes_return_failed());commands++;
 assert(commands<4096);command_kind[commands]=cmd_number;command_stage[commands]=stage;
 if(cmd_number==24)write_commands++;else read_commands++;
 command_fault=(fault==END_BAD||fault==BUSY_FOREVER)?(cmd_number==24&&write_commands==fault_at):commands==fault_at;
 if(fault==READ_ALTER&&!fault_at)command_fault=stage==7&&cmd_number==17;
 response_rise=rises;read_start=rises+52;data_end=0;samples=0;
 memset(response,0,6);response[0]=(uint8_t)cmd_number;response[3]=9;
 crc=0;for(unsigned i=0;i<5;i++)crc=crc7update(crc,response[i]);response[5]=(uint8_t)((crc<<1)|1);
 if(command_fault&&fault==R1_BAD)response[5]^=2;
 memset(write_data,0,512);memset(write_crc,0,sizeof(write_crc));memset(write_seen,0,sizeof(write_seen));
 if(cmd_number==17){
  memcpy(read_data,media+cmd_sector*512u,512);
  if(command_fault&&fault==READ_ALTER)read_data[0]^=1;
  memset(read_crc,0,sizeof(read_crc));for(unsigned i=0;i<1024;i++)crc_nibble(read_crc,(read_data[i/2]>>((i&1)?0:4))&15);
  if(command_fault&&fault==READ_CRC_BAD)read_crc[0]^=1;
 }
}
static void set_pin(unsigned pin,unsigned value){
 if(pin==CMD){cmd_value=value;cmd_pending=1;return;}
 if(pin>=DAT0){data_value=(data_value&~(1u<<(pin-DAT0)))|(value<<(pin-DAT0));return;}
 assert(pin==CLK);
 if(level&&!value&&receiving)falls++;
 if(!level&&value){
  rises++;
  if(cmd_pending){assert(cmd_bits<48);cmd_wire[cmd_bits/8]=(uint8_t)((cmd_wire[cmd_bits/8]<<1)|cmd_value);cmd_bits++;cmd_pending=0;}
  if(data_mask==15){
   assert(cmd_number==24);unsigned n=samples++;
   if(n==0)assert(data_value==0);
   else if(n<=1024){unsigned at=n-1;write_data[at/2]=(uint8_t)((write_data[at/2]<<4)|data_value);crc_nibble(write_crc,data_value);}
   else if(n<=1040)for(unsigned i=0;i<4;i++)write_seen[i]=(uint16_t)((write_seen[i]<<1)|((data_value>>i)&1));
   else {assert(n==1041&&data_value==15);for(unsigned i=0;i<4;i++)assert(write_seen[i]==write_crc[i]);data_end=rises;
    /* A bad host-observed response may follow a card-side commit. Do not
     * promise rollback or retry an uncertain write. */
    memcpy(media+cmd_sector*512u,write_data,512);commits++;
   }
  }
 }
 level=value;
}
static unsigned input(unsigned pin){
 if(pin==CMD){if((command_fault&&fault==R1_TIMEOUT)||!receiving||falls<2||falls>=50)return 1;unsigned n=falls-2;return(response[n/8]>>(7-n%8))&1;}
 assert(pin==DAT0&&data_mask==0);
 if(cmd_number==17)return (command_fault&&fault==DATA_TIMEOUT)||rises<read_start?1:0;
 if(!data_end)return 1;
 unsigned n=rises-data_end;
 if(n>=3&&n<=6)return(2u>>(6-n))&1;
 if(n==7)return !(command_fault&&fault==END_BAD);
 if(n>=8&&(n-8<busy_clocks||(command_fault&&fault==BUSY_FOREVER)))return 0;
 return 1;
}
static unsigned data_in(void){
 assert(cmd_number==17&&rises>read_start);unsigned n=rises-read_start-1;
 if(n<1024){read_nibbles++;return(read_data[n/2]>>((n&1)?0:4))&15;}
 if(n<1040){unsigned d=0;for(unsigned i=0;i<4;i++)d|=((read_crc[i]>>(1039-n))&1)<<i;return d;}
 assert(n==1040);return 15;
}
static void mode_in(unsigned pin){if(pin==CMD){start_response();receiving=1;falls=0;}else data_mask&=~(1u<<(pin-DAT0));}
static void mode_out(unsigned pin){if(pin==CMD){receiving=0;cmd_bits=cmd_pending=0;memset(cmd_wire,0,6);}else data_mask|=1u<<(pin-DAT0);}
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
#define SD_DAT_IN data_in()
#define SD_DAT_OUT(n) (data_value=(n))
#define OUT_BIT(r,p,n) set_pin(p,n)
#define __DSB() ((void)0)
#define __NOP() ((void)0)
#define DBG_SD if(0)
#define DBG_SD_OFFLOAD if(0)
#define MAX_CARDS 1
#define SDCARD_DETECT card
#define SDCARD_WP wp
#include "native.inc"
DSTATUS disk_initialize(BYTE d){assert(!d);return 0;}
DSTATUS disk_status(BYTE d){assert(!d);return 0;}
DRESULT disk_read(BYTE d,BYTE *p,DWORD s,UINT n){return sdn_read(d,p,s,n);}
DRESULT disk_write(BYTE d,const BYTE *p,DWORD s,UINT n){
 DRESULT result=sdn_write(d,p,s,n);
 if(result==RES_OK)assert(data_end&&samples==1042&&rises-data_end-7>=8);
 return result;
}
DRESULT disk_ioctl(BYTE d,BYTE c,void *p){syncs++;return sdn_ioctl(d,c,p);}
DWORD get_fattime(void){return (DWORD)(2026-1980)<<25|10u<<21|8u<<16;}
static void word(unsigned at,unsigned n){media[at]=(uint8_t)n;media[at+1]=(uint8_t)(n>>8);}
static void dword(unsigned at,uint32_t n){for(unsigned i=0;i<4;i++)media[at+i]=(uint8_t)(n>>(8*i));}
static void reset_case(unsigned fat32){
 nes_diag_leave();nes_return_reset();nes_diag_sd_reset();(void)f_mount(NULL,"",0);
 stage=2;stage_mask=commands=write_commands=read_commands=commits=read_nibbles=syncs=0;
 first_fault_stage=first_fault_command=first_fault_rises=0;
 level=rises=falls=receiving=cmd_pending=cmd_value=cmd_bits=cmd_number=cmd_sector=0;
 data_end=samples=data_mask=data_value=fault=fault_at=command_fault=busy_clocks=wp=tick_div=tick_origin=0;
 during_blocktrans=TRANS_NONE;sd_offload=ff_sd_offload=sd_offload_partial=0;ccs=card=1;disk_state=DISK_OK;
 sectors=fat32?70000:8192;memset(media,0,sizeof(media));memset(&fs,0,sizeof(fs));
 media[0]=0xeb;media[1]=0x3c;media[2]=0x90;memcpy(media+3,"REPORT78",8);word(11,512);media[13]=1;media[16]=2;media[21]=0xf8;word(510,0xaa55);
 if(!fat32){memcpy(media+54,"FAT16   ",8);word(14,1);word(17,512);word(19,8192);word(22,32);root_sector=65;for(unsigned i=0;i<2;i++){word((1+i*32)*512,0xfff8);word((1+i*32)*512+2,0xffff);}}
 else {memcpy(media+82,"FAT32   ",8);word(14,32);dword(32,70000);dword(36,547);dword(44,2);word(48,1);root_sector=1126;
  for(unsigned i=0;i<2;i++){unsigned at=(32+i*547)*512;dword(at,0x0ffffff8);dword(at+4,0x0fffffff);dword(at+8,0x0fffffff);}
  dword(512,0x41615252);dword(512+484,0x61417272);dword(512+488,0xffffffff);dword(512+492,2);word(512+510,0xaa55);
 }
 nes_diag_begin();nes_return_io_begin();assert(f_mount(&fs,"",1)==FR_OK&&fs.fs_type==(fat32?FS_FAT32:FS_FAT16));
 /* Mount is exercised through native CMD17 too; fault indexes below are
  * relative to report operations, with its own write-window budget. */
 commands=read_commands=write_commands=read_nibbles=0;
}
static char report[6144],path[16];
static void verify_saved(unsigned len){
 assert(!nes_return_log_allowed()&&!nes_return_failed()&&nes_diag_active());
 assert(stage_mask==0x1fc&&commits==write_commands&&syncs>=1);
 /* Drop all FatFS state to exclude cached directory/data success. */
 assert(f_mount(NULL,"",0)==FR_OK);memset(&fs,0,sizeof(fs));assert(f_mount(&fs,"",1)==FR_OK);
 FIL f;UINT got=0;char back[6144];assert(f_open(&f,path,FA_READ)==FR_OK&&f_size(&f)==len);
 assert(f_read(&f,back,len,&got)==FR_OK&&got==len&&!memcmp(report,back,len)&&f_close(&f)==FR_OK);
}
static void run_family(unsigned fat32,unsigned len){
 reset_case(fat32);int result=sdinv_write_report(report,len,path,sizeof(path));assert(result==0);
 unsigned total=commands,total_writes=write_commands,total_rises=rises;
 unsigned reads[4096],read_count=0;
 for(unsigned n=1;n<=total;n++)if(command_kind[n]==17)reads[read_count++]=n;
 for(unsigned n=1;n<=total;n++)printf("WIRE078 command=%u CMD%u stage=%u\n",n,command_kind[n],command_stage[n]);
 printf("NORMAL078 FAT%u bytes=%u commands=%u writes=%u edges=%u ticks=%lu stages=%x\n",fat32?32:16,len,total,total_writes,total_rises,(unsigned long)nes_diag_ticks(),stage_mask);
 verify_saved(len);checks++;
 /* Every wire command response must propagate through the real report. */
 for(unsigned n=1;n<=total;n++){
  reset_case(fat32);fault=R1_BAD;fault_at=n;result=sdinv_write_report(report,len,path,sizeof(path));
  assert(result==8&&nes_return_failed()&&!nes_return_log_allowed()&&commands==n&&first_fault_command==n);
  unsigned before=rises;uint8_t b[512];assert(disk_read(0,b,0,1)!=RES_OK&&disk_write(0,b,0,1)!=RES_OK&&rises==before);checks++;
 }
 for(unsigned n=1;n<=total_writes;n++){
  reset_case(fat32);fault=END_BAD;fault_at=n;result=sdinv_write_report(report,len,path,sizeof(path));
  assert(result==8&&nes_return_failed()&&!nes_return_log_allowed()&&write_commands==n&&commits==n);
  assert(first_fault_stage>=2&&first_fault_stage<=5);checks++;
 }
 for(unsigned i=0;i<read_count;i++){
  reset_case(fat32);fault=READ_CRC_BAD;fault_at=reads[i];result=sdinv_write_report(report,len,path,sizeof(path));
  assert(result==8&&nes_diag_status()->error==NES_DIAG_SD_CRC&&commands==reads[i]&&!nes_return_log_allowed());checks++;
 }
 printf("FAULT078 FAT%u all_command_positions=%u all_write_end_positions=%u\n",fat32?32:16,total,total_writes);
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,NULL,_IONBF,0);
 struct sdinv_report info={0};info.finished=1;for(unsigned i=0;i<SDINV_FILES;i++)info.files[i].status=SDINV_ABSENT;
 int len=sdinv_format(&info,report,sizeof(report));assert(len>0&&len<6144);
 for(unsigned fat=0;fat<2;fat++)run_family(fat,(unsigned)len);
 for(unsigned i=0;i<sizeof(report);i++)report[i]=(char)(i*73+19);
 const unsigned sizes[]={1,511,512,513,4500,6143};
 for(unsigned fat=0;fat<2;fat++)for(unsigned n=0;n<6;n++){
  reset_case(fat);ccs=n&1;busy_clocks=n;assert(sdinv_write_report(report,sizes[n],path,sizeof(path))==0);verify_saved(sizes[n]);checks++;
 }
 for(unsigned fat=0;fat<2;fat++){
  reset_case(fat);fault=READ_ALTER;fault_at=0;int result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==7&&!nes_return_failed()&&!nes_return_log_allowed()&&sdinv_save_detail()->operation==6);checks++;
  reset_case(fat);fault=READ_CRC_BAD;fault_at=1;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&nes_diag_status()->error==NES_DIAG_SD_CRC&&!nes_return_log_allowed());checks++;
  reset_case(fat);fault=BUSY_FOREVER;fault_at=1;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&nes_diag_status()->error==NES_DIAG_SD_BUSY&&rises-first_fault_rises==0&&!nes_return_log_allowed());checks++;
  reset_case(fat);fault=BUSY_FOREVER;fault_at=1;tick_div=10;tick_origin=UINT32_MAX-5;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&nes_diag_status()->error==NES_DIAG_SD_BUSY&&rises<10000&&!nes_return_log_allowed());checks++;
  reset_case(fat);fault=R1_TIMEOUT;fault_at=1;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&commands==1&&nes_diag_status()->error==NES_DIAG_SD_RESPONSE&&!nes_return_log_allowed());checks++;
  reset_case(fat);fault=DATA_TIMEOUT;fault_at=1;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&commands==1&&nes_diag_status()->error==NES_DIAG_SD_DATA&&!nes_return_log_allowed());checks++;
  reset_case(fat);tick_div=10;tick_origin=UINT32_MAX-5;result=sdinv_write_report(report,6143,path,sizeof(path));assert(result==8&&nes_return_failed()&&!nes_return_log_allowed());printf("BUDGET078 FAT%u error=%u stage=%u edges=%u wrap=1\n",fat?32:16,nes_diag_status()->error,first_fault_stage,rises);checks++;
  reset_case(fat);wp=1;result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==4&&!nes_return_log_allowed()&&!write_commands&&!nes_return_failed());checks++;
  /* Existing filename requires CREATE_NEW to select the next slot. */
  reset_case(fat);assert(sdinv_write_report(report,513,path,sizeof(path))==0);
  assert(sdinv_write_report(report,511,path,sizeof(path))==0&&!strcmp(path,"/HW005001.TXT"));verify_saved(511);checks++;
  /* Force non-contiguous allocation; no input file is used as test storage. */
  reset_case(fat);
  for(unsigned i=0;i<2;i++)for(unsigned cluster=4;cluster<48;cluster+=2){
   if(fat)dword((32+i*547)*512+cluster*4,0x0fffffff);else word((1+i*32)*512+cluster*2,0xffff);
  }
  assert(sdinv_write_report(report,6143,path,sizeof(path))==0);verify_saved(6143);checks++;
  /* With frozen ticks, a full FAT allocation scan must exhaust the shared
   * poll budget instead of scanning indefinitely or bypassing the guard. */
  reset_case(fat);
  for(unsigned i=0;i<2;i++)for(unsigned cluster=2;cluster<fs.n_fatent;cluster++){
   if(fat)dword((32+i*547)*512+cluster*4,0x0fffffff);else word((1+i*32)*512+cluster*2,0xffff);
  }
  result=sdinv_write_report(report,4500,path,sizeof(path));assert(result==8&&nes_return_failed()&&nes_diag_status()->error==NES_DIAG_MENU&&!nes_return_log_allowed());checks++;
 }
 printf("PASS078 checks=%u native_read_write=1 actual_FatFS=1 cold_remount=1 physical=0\n",checks);return 0;
}
