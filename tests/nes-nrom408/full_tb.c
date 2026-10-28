// SPDX-License-Identifier: MIT
// Exact generated 227 loader function + actual verify/framing, modeled file,
// SPI/PSRAM and run/display. This is not actual FatFS/FPGA hardware.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_nrom406.h"
#include "nes_menu_probe.h"
#ifdef NROM_USE_FATFS
#include "ff.h"
#include "diskio.h"
void nrom_fatdisk_prepare(const uint8_t *,uint32_t);
void nrom_fatdisk_mutate(uint32_t);
static FATFS fatfs;
#else
typedef unsigned UINT;
typedef struct {uint32_t fptr,fsize;} FIL;
#define FR_OK 0
#define FA_READ 1
#endif
#define NES_DIAG_SD_STATE 1
#define NES_DIAG_SPI 2
#define NES_DIAG_VALIDATE 3
#define NES_DIAG_LOAD 4
#define NES_DIAG_CHECK 5
#define NES_DIAG_CONFIG 6
#define NES_DIAG_BLOCKED 7
#define NES_DIAG_RECOVER 8
#define SPI_SR_BSY 1u
#define SPI_SR_TXE 2u
#define OTG_FS_IRQn 67
#define FPGA_BASE "base"
#define FPGA_TEST_TOKEN 0xa5
struct hw_spi {uint32_t SR;};static struct hw_spi hw;static struct hw_spi *SPI1=&hw;
struct diagnostic {unsigned error;};static struct diagnostic diagnostic;
static uint8_t filedata[24592],memory[0x60000];
static uint32_t count,check_next;static unsigned opens,closes,config_count,stop_count,start_count,irq_count;
static uint8_t flags,board_id;static bool sticky,return_failed,gpio_owned,reset_held;
static int scenario;
enum {OK=0, BAD_HEADER=1, WRONG_ID=2, MUTATE_SECOND=3, MUTATE_THIRD=4,
      WRITE_FAILURE=5, READ_CORRUPT=6, STOP_FAILURE=7, BASE_FAILURE=8};
#ifdef NROM_USE_FATFS
static FRESULT nrom_open(FIL *f,const char *path,unsigned mode){
 opens++;
 if(scenario==MUTATE_THIRD&&opens==2)nrom_fatdisk_mutate(100);
 return f_open(f,path,(BYTE)mode);
}
static FRESULT nrom_seek(FIL *f,DWORD at){
 FRESULT r=f_lseek(f,at);
 if(scenario==MUTATE_SECOND)nrom_fatdisk_mutate(100);
 return r;
}
static FRESULT nrom_close(FIL *f){closes++;return f_close(f);}
#define f_open nrom_open
#define f_lseek nrom_seek
#define f_close nrom_close
#else
static unsigned f_open(FIL *f,const char *path,unsigned mode){
 (void)path;assert(mode==FA_READ);opens++;f->fptr=0;f->fsize=sizeof(filedata);
 if(scenario==MUTATE_THIRD&&opens==2)filedata[100]^=1;
 return FR_OK;
}
static unsigned f_read(FIL *f,uint8_t *buf,UINT n,UINT *got){
 if(f->fptr+n>f->fsize){*got=0;return 1;}
 memcpy(buf,filedata+f->fptr,n);f->fptr+=n;*got=n;return FR_OK;
}
static unsigned f_lseek(FIL *f,uint32_t at){if(at>f->fsize)return 1;f->fptr=at;if(scenario==MUTATE_SECOND)filedata[100]^=1;return FR_OK;}
static unsigned f_close(FIL *f){(void)f;closes++;return FR_OK;}
static uint32_t f_size(FIL *f){return f->fsize;}
static uint32_t f_tell(FIL *f){return f->fptr;}
#endif
static void load_select(void *ctx,bool value){(void)ctx;(void)value;}
static void load_clock(void *ctx,bool value){(void)ctx;(void)value;}
static void load_mosi(void *ctx,bool value){(void)ctx;(void)value;}
static bool load_miso(void *ctx){(void)ctx;return false;}
static void wait_us(void *ctx,unsigned value){(void)ctx;(void)value;}
static bool NVIC_GetEnableIRQ(int n){assert(n==OTG_FS_IRQn);return true;}
static void NVIC_DisableIRQ(int n){assert(n==OTG_FS_IRQn);}
static void NVIC_EnableIRQ(int n){assert(n==OTG_FS_IRQn);irq_count++;}
static void snes_reset(int n){reset_held=n!=0;}
static bool nes_diag_sd_handoff113(void){return true;}
static void nes_return_fail(int n){(void)n;return_failed=true;}
static bool nes_return_failed(void){return return_failed;}
static bool nes_checkpoint_begin112(void){return true;}
static bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;return true;}
static bool nes_cf86_enter094(void){sticky=false;return true;}
bool nes_cf86_monitoring094(void){return true;}
bool nes_cf86_check094(void){return !sticky;}
bool nes_cf86_fail094(void){sticky=true;return false;}
static bool nes_cf86_failed094(void){return sticky;}
static bool nes_cf86_finish094(void){return !sticky;}
static bool nes_css_begin108(void){return true;}
static bool nes_menu_entry_only113(void){return false;}
static bool nes_menu_base_only116(void){return false;}
static void nes_diag_progress(int s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;}
static bool nes_diag_fpga_pgm(const uint8_t *p){(void)p;config_count++;return !(scenario==BASE_FAILURE&&config_count==2);}
static bool configured(const char *p){(void)p;return true;}
static bool nes_return_spi_ready(void){return true;}
static bool nes_cf86_arm094(void){return true;}
static bool slow_begin(void){gpio_owned=true;return true;}
static void cf86_end094(void){gpio_owned=false;}
static bool nes_diag_sd_failed(void){return false;}
static struct diagnostic *nes_diag_status(void){return &diagnostic;}
static uint8_t fpga_test(void){return FPGA_TEST_TOKEN;}
static bool nes_menu_diagnostic_pending(void){return false;}
static void nes_diag_leave(void){}
static bool identify136(const struct nes_rom_spi_io *,struct nes_menu_probe_report *);
static bool run136(const struct nes_rom_spi_io *,uint32_t,struct nes_mcu_load_report *,uint32_t);
#include "full408.inc"
static bool identify136(const struct nes_rom_spi_io *io,struct nes_menu_probe_report *p){
 struct nes_rom_spi_status s={0};if(!sd_query(io,&s)||s.flags||s.count)return false;
 p->board_seen=true;p->board_id=0x78;return true;
}
static bool run136(const struct nes_rom_spi_io *io,uint32_t total,struct nes_mcu_load_report *r,uint32_t epoch){
 (void)epoch;if(!nes_rom_verified_start(io,total))return false;
 uint8_t tx[8],rx[8];struct nes_rom_spi_status s={0};nes_rom_spi_frame(tx,NES_ROM_STOP,total,0);
 if(!nes_rom_spi_transfer(io,tx,rx)||!sd_query(io,&s)||s.flags!=2||s.count!=total)return nes_cf86_fail094();
 r->stop_ok=true;return true;
}
bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;if(sticky)return false;
 uint32_t at=((uint32_t)tx[1]<<16)|((uint32_t)tx[2]<<8)|tx[3];
 uint8_t check[8];nes_rom_spi_frame(check,tx[0],at,tx[4]);assert(!memcmp(check,tx,8));
 memset(rx,0,8);rx[1]=board_id;uint32_t reply_count=count;
 switch(tx[0]){
 case NES_ROM_STATUS:rx[2]=flags;break;
 case NES_ROM_BEGIN:assert(!flags&&!count&&at==0&&tx[4]==2);flags=1;break;
 case NES_ROM_DATA:
  assert(flags==1&&at==count&&count<sizeof(memory));
  if(scenario==WRITE_FAILURE&&count==0x40001)return false;
  memory[count++]=tx[4];break;
 case NES_ROM_END:assert(flags==1&&at==count&&count==sizeof(memory));flags=2;break;
 case 0x66:assert(flags==2&&at==0);flags=0x22;check_next=0;break;
 case 0x67:assert(flags==0x22&&at==check_next);flags=0x62;break;
 case 0x6a:assert(flags==0x62);rx[2]=flags;reply_count=check_next;rx[3]=memory[check_next];
  if(scenario==READ_CORRUPT&&check_next==0x40000)rx[3]^=1;
  break;
 case 0x68:assert(flags==0x62&&at==check_next&&tx[4]==memory[check_next]);check_next++;flags=0x22;break;
 case 0x69:assert(flags==0x22&&at==count&&check_next==count);flags=0x82;break;
 case NES_ROM_START:assert(flags==0x82&&at==count);flags=0x86;start_count++;break;
 case NES_ROM_STOP:stop_count++;if(scenario==STOP_FAILURE)return false;
  if(flags==0x86)flags=2;else {flags=0;count=0;}break;
 default:assert(0);
 }
 rx[4]=reply_count>>16;rx[5]=reply_count>>8;rx[6]=reply_count;return true;
}
static void fresh(int test){
 scenario=test;memset(filedata,0,sizeof(filedata));memset(memory,0xcc,sizeof(memory));
 filedata[0]='N';filedata[1]='E';filedata[2]='S';filedata[3]=0x1a;filedata[4]=1;filedata[5]=1;
 for(uint32_t i=16;i<sizeof(filedata);i++)filedata[i]=(uint8_t)(i^(i>>8)^0xa5);
 if(test==BAD_HEADER)filedata[6]=1;
#ifdef NROM_USE_FATFS
 nrom_fatdisk_prepare(filedata,sizeof(filedata));
 assert(f_mount(&fatfs,"",1)==FR_OK);
#endif
 flags=count=check_next=opens=closes=config_count=stop_count=start_count=irq_count=0;
 board_id=test==WRONG_ID?0x74:0x78;sticky=return_failed=gpio_owned=reset_held=false;hw.SR=SPI_SR_TXE;
}
int main(void){
 struct nes_menu_probe_report p;
 for(int i=OK;i<=BASE_FAILURE;i++){
  fresh(i);bool safe=nes_menu_sd_probe("nrom.nes","nrom.bi3",false,&p);
  assert(reset_held);
  if(i==OK){
   assert(safe&&p.sd.verified&&p.sd.load.base_restored&&p.sd.load.stop_ok);
   assert(start_count==1&&stop_count==1&&config_count==2&&irq_count==1&&opens==2&&closes==2);
   assert(!memcmp(memory,filedata+16,16384));assert(!memcmp(memory+0x40000,filedata+16400,8192));
   for(uint32_t j=16384;j<0x40000;j++)assert(memory[j]==0);
   for(uint32_t j=0x42000;j<0x60000;j++)assert(memory[j]==0);
  }else if(i==BAD_HEADER){assert(safe&&!p.sd.verified&&!start_count&&!config_count);}
  else {assert(!safe&&!p.sd.verified&&!irq_count);if(i!=STOP_FAILURE&&i!=BASE_FAILURE)assert(!start_count);}
  printf("NROM408 case=%d safe=%d start=%u stop=%u configs=%u verified=%d sticky=%d\n",i,safe,start_count,stop_count,config_count,p.sd.verified,sticky);
 }
#ifdef NROM_USE_FATFS
 puts("NROM408 COMPLETE 227 loader function actual FatFS, modeled disk/SPI/PSRAM/run; no physical FPGA");
#else
 puts("NROM408 COMPLETE 227 loader function modeled file/SPI/PSRAM/run; not physical FPGA/FatFS");
#endif
 return 0;
}
