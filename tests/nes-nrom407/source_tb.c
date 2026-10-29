// SPDX-License-Identifier: MIT
// Includes exact generated 407 load_crc/load_read/sd_source, compiled with
// the generated real 227 verifier. File and SPI/PSRAM are modeled here.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_nrom406.h"
#include "nes_rom_verify.h"
#include "nes_mcu_loader.h"
typedef unsigned UINT;
typedef struct {uint8_t data[24592];uint32_t position,size;int close_error;} FIL;
#define FR_OK 0
#define NES_DIAG_CHECK 0
static unsigned f_read(FIL *f, uint8_t *b, UINT n, UINT *got){
 if(f->position+n>f->size){*got=0;return 1;}
 memcpy(b,f->data+f->position,n);f->position+=n;*got=n;return 0;
}
static uint32_t f_size(FIL *f){return f->size;}
static uint32_t f_tell(FIL *f){return f->position;}
static unsigned f_close(FIL *f){return f->close_error?1:0;}
static void nes_diag_progress(int stage,uint32_t at,uint32_t total){(void)stage;(void)at;(void)total;}
#include "source407.inc"
static uint8_t physical[0x60000];
static uint32_t next;
static uint8_t flags,board_id;
static bool sticky,started;
bool nes_cf86_monitoring094(void){return true;}
bool nes_cf86_fail094(void){sticky=true;return false;}
bool nes_cf86_check094(void){return !sticky;}
bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;if(sticky)return false;
 uint32_t a=((uint32_t)tx[1]<<16)|((uint32_t)tx[2]<<8)|tx[3];
 uint8_t check[8];nes_rom_spi_frame(check,tx[0],a,tx[4]);assert(!memcmp(check,tx,8));
 memset(rx,0,8);rx[1]=board_id;uint32_t count=0x60000;
 switch(tx[0]){
 case 0x65:rx[2]=flags;break;
 case 0x66:assert(flags==2&&a==0);flags=0x22;break;
 case 0x67:assert(flags==0x22&&a==next);flags=0x62;break;
 case 0x6a:assert(flags==0x62);rx[2]=flags;count=next;rx[3]=physical[next];break;
 case 0x68:assert(flags==0x62&&a==next&&tx[4]==physical[next]);next++;flags=0x22;break;
 case 0x69:assert(flags==0x22&&a==0x60000&&next==a);flags=0x82;break;
 case 0x63:assert(flags==0x82&&a==0x60000);flags=0x86;started=true;break;
 default:assert(0);
 }
 rx[4]=count>>16;rx[5]=count>>8;rx[6]=count;return true;
}
static void fresh(FIL *f,struct sd_source_context *c,struct nes_mcu_load_report *r,bool *opened,uint8_t *buffer){
 memset(f,0,sizeof(*f));f->size=24592;
 f->data[0]='N';f->data[1]='E';f->data[2]='S';f->data[3]=0x1a;f->data[4]=1;f->data[5]=1;
 for(uint32_t i=16;i<f->size;i++)f->data[i]=(uint8_t)(i^(i>>8)^0xa5);
 struct nes_nrom406_profile profile;assert(nes_nrom406_header(f->data,f->size,&profile));
 memset(physical,0,sizeof(physical));memcpy(physical,f->data+16,16384);memcpy(physical+0x40000,f->data+16400,8192);
 uint32_t crc=load_crc(0xffffffffu,f->data,f->size)^0xffffffffu;
 memset(r,0,sizeof(*r));*opened=true;f->position=16;
 *c=(struct sd_source_context){f,r,opened,0x60000,crc,load_crc(0xffffffffu,f->data,16),0,buffer,profile};
 next=0;flags=2;board_id=0x78;sticky=started=false;
}
int main(void){
 FIL file;struct sd_source_context c;struct nes_mcu_load_report lr;bool opened;uint8_t buffer[256];
 struct nes_rom_spi_io io={0};struct nes_verify_report vr;
 fresh(&file,&c,&lr,&opened,buffer);
 assert(nes_rom_verify(&io,0x60000,sd_source,&c,&vr)&&vr.compared==0x60000&&!opened&&file.position==file.size);
 assert(nes_rom_verified_start(&io,0x60000)&&started);
 const uint32_t faults[]={0,0x8000,0x40000,0x5ffff};
 for(unsigned i=0;i<4;i++){
  fresh(&file,&c,&lr,&opened,buffer);physical[faults[i]]^=1;
  assert(!nes_rom_verify(&io,0x60000,sd_source,&c,&vr));
  assert(vr.error==NES_VERIFY_DATA&&vr.compared==faults[i]&&sticky&&!started&&!vr.stop_ok);
 }
 fresh(&file,&c,&lr,&opened,buffer);c.expected_crc^=1;
 assert(!nes_rom_verify(&io,0x60000,sd_source,&c,&vr)&&vr.error==NES_VERIFY_SOURCE&&sticky&&!started);
 fresh(&file,&c,&lr,&opened,buffer);file.close_error=1;
 assert(!nes_rom_verify(&io,0x60000,sd_source,&c,&vr)&&vr.error==NES_VERIFY_SOURCE&&sticky&&!started);
 fresh(&file,&c,&lr,&opened,buffer);board_id=0x74;
 assert(!nes_rom_verify(&io,0x60000,sd_source,&c,&vr)&&vr.error==NES_VERIFY_PROTOCOL&&!started);
 fresh(&file,&c,&lr,&opened,buffer);file.position++;
 uint8_t byte;assert(!sd_source(&c,0,&byte)&&lr.result==NES_MCU_LOAD_CHANGED);
 fresh(&file,&c,&lr,&opened,buffer);
 assert(!sd_source(&c,1,&byte)&&lr.result==NES_MCU_LOAD_CHANGED);
 puts("NROM407 actual sd_source and verifier PASS: data4 CRC close ID rejection, no hardware STOP proof");
 return 0;
}
