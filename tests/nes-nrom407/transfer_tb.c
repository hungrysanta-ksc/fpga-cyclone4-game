// SPDX-License-Identifier: MIT
// Exact generated 227 validation and write sections, mocked FatFS and SPI.
// No FPGA implementation, full menu loader, physical STOP or base restore.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_nrom406.h"
#include "nes_rom_spi.h"
#include "nes_mcu_loader.h"
typedef unsigned UINT;
typedef struct {uint8_t data[24592];uint32_t position,size;int close_error;} FIL;
#define FR_OK 0
#define NES_DIAG_VALIDATE 0
#define NES_DIAG_LOAD 1
static unsigned f_read(FIL *f,uint8_t *b,UINT n,UINT *got){
 if(f->position+n>f->size){*got=0;return 1;}
 memcpy(b,f->data+f->position,n);f->position+=n;*got=n;return 0;
}
static uint32_t f_size(FIL *f){return f->size;}
static uint32_t f_tell(FIL *f){return f->position;}
static unsigned f_close(FIL *f){return f->close_error?1:0;}
static unsigned f_lseek(FIL *f,uint32_t n){if(n>f->size)return 1;f->position=n;return 0;}
static void nes_diag_progress(int stage,uint32_t at,uint32_t total){(void)stage;(void)at;(void)total;}
static bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;return true;}
static uint8_t peer[0x60000];static uint32_t count,fail_at;static bool begun,ended,mutate;
static bool sd_command(const struct nes_rom_spi_io *io,uint8_t op,uint32_t at,uint8_t data,struct nes_rom_spi_status *status){
 (void)io;(void)status;
 if(op==NES_ROM_BEGIN){assert(!begun&&!count&&at==0&&data==2);begun=true;return true;}
 if(op==NES_ROM_DATA){assert(begun&&!ended&&at==count);if(at==fail_at)return false;peer[count++]=data;return true;}
 if(op==NES_ROM_END){assert(begun&&!ended&&at==0x60000&&count==at);ended=true;return true;}
 assert(0);return false;
}
#include "transfer407.inc"
static void fresh(FIL *f){
 memset(f,0,sizeof(*f));f->size=24592;
 f->data[0]='N';f->data[1]='E';f->data[2]='S';f->data[3]=0x1a;f->data[4]=1;f->data[5]=1;
 for(uint32_t i=16;i<f->size;i++)f->data[i]=(uint8_t)(i^(i>>8)^0xa5);
 memset(peer,0xcc,sizeof(peer));count=0;begun=ended=mutate=false;fail_at=0xffffffffu;
}
int main(void){
 FIL file;struct nes_mcu_load_report report;
 fresh(&file);assert(test_transfer407(&file,&report));
 assert(begun&&ended&&report.end_accepted&&count==0x60000);
 assert(!memcmp(peer,file.data+16,16384));
 for(uint32_t i=16384;i<0x40000;i++)assert(peer[i]==0);
 assert(!memcmp(peer+0x40000,file.data+16400,8192));
 for(uint32_t i=0x42000;i<0x60000;i++)assert(peer[i]==0);
 fresh(&file);file.data[6]=1;assert(!test_transfer407(&file,&report)&&!begun&&!ended);
 fresh(&file);file.size--;assert(!test_transfer407(&file,&report)&&!begun&&!ended);
 fresh(&file);mutate=true;assert(!test_transfer407(&file,&report)&&begun&&!ended&&report.result==NES_MCU_LOAD_CHANGED);
 fresh(&file);fail_at=0x40001;assert(!test_transfer407(&file,&report)&&begun&&!ended&&report.result==NES_MCU_LOAD_SPI);
 fresh(&file);file.close_error=1;assert(!test_transfer407(&file,&report)&&begun&&!ended&&report.result==NES_MCU_LOAD_CLOSE);
 puts("NROM407 exact 227 validation/write sections PASS fixed profile, padding, CRC and injected failures; no STOP/base proof");
 return 0;
}
