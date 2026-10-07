/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <crtdbg.h>
#endif
#include "fileops.h"
#include "smc.h"
#include "sgb.h"
#include "cfg.h"
#include "fpga_spi.h"
cfg_t CFG;
struct file_mock file_handle;
unsigned file_res;
static uint8_t image[0x400200];
static unsigned reads,short_at,failed;
uint32_t file_readblock(void *dst,uint32_t at,unsigned size){
 reads++;file_res=0;
 if(reads==short_at){failed=1;return 0;}
 if(at>file_handle.fsize||size>file_handle.fsize-at)return 0;
 memcpy(dst,image+at,size);return size;
}
uint32_t crc32_update(uint32_t c,uint8_t b){c^=b;for(unsigned n=0;n<8;n++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);return c;}
extern snes_romprops_t romprops;
extern sgb_romprops_t sgb_romprops;
static unsigned nes_return_failed(void){return failed;}
#include "actual-return-gate.inc"
static void identify(void){
 memset(&romprops,0,sizeof(romprops));memset(&sgb_romprops,0,sizeof(sgb_romprops));
 reads=failed=file_res=0;
 sgb_id(&sgb_romprops,(uint8_t *)"/sd2snes/m3nu.bin");
 smc_id(&romprops,0);
}
int main(int argc,char **argv){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 _set_error_mode(_OUT_TO_STDERR);
 _set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
 assert(!fseek(f,0,SEEK_END));long length=ftell(f);assert(length==65536);
 rewind(f);file_handle.fsize=(uint32_t)length;assert(fread(image,1,(size_t)length,f)==(size_t)length);assert(!fclose(f));
 _Static_assert(sizeof(snes_header_t)==80,"actual packed SNES header");
 identify();
 assert(!failed&&!romprops.error&&romprops.header_address==0xffb0&&romprops.offset==0);
 assert(romprops.mapper_id==0&&romprops.header.map==0x31&&romprops.header.carttype==0x55);
 assert(romprops.romsize_bytes==65536&&romprops.ramsize_bytes==8192&&romprops.sramsize_bytes==8192);
 assert(romprops.fpga_features==FEAT_SRTC&&!romprops.fpga_conf&&!romprops.load_address);
 assert(!sgb_romprops.has_sgb&&!sgb_romprops.has_egbc);
 assert(actual_return_rejected(file_handle.fsize));
 printf("ACTUAL075 header=%x mapper=%u map=%x carttype=%x ROM=%u SRAM=%u features=%x reads=%u current_gate=REJECT\n",romprops.header_address,romprops.mapper_id,romprops.header.map,romprops.header.carttype,romprops.romsize_bytes,romprops.sramsize_bytes,romprops.fpga_features,reads);
 unsigned count=1;
 /* Isolate the actual rejecting predicate; does not approve modified images. */
 romprops.header.carttype=0;assert(!actual_return_rejected(file_handle.fsize));count++;
 romprops.header.carttype=0x55;assert(actual_return_rejected(file_handle.fsize));count++;
#ifdef GUARDED_CLASSIFIER
 unsigned normal_reads=reads;
 /* Inject a short successful-return read at every original read site. Expected
  * out-of-range header probes stay ordinary absent candidates, not I/O errors. */
 for(unsigned n=1;n<=normal_reads;n++){
  short_at=n;identify();assert(failed);assert(actual_return_rejected(file_handle.fsize));count++;
 }
 short_at=0;
 const unsigned fields[]={40,13};
 for(unsigned field=0;field<sizeof(fields)/sizeof(fields[0]);field++){
  unsigned offset=fields[field];uint8_t old=image[0xffb0+offset];image[0xffb0+offset]=32;
  identify();assert(romprops.error);image[0xffb0+offset]=old;count++;
 }
 /* No viable header: fail before using default/stale LoROM fields. */
 memset(image,0,sizeof(image));identify();assert(romprops.error);count++;
#endif
 printf("PASS075 actual_menu checks=%u guarded=%u hardware=0\n",count,
#ifdef GUARDED_CLASSIFIER
 1u
#else
 0u
#endif
 );return 0;
}
