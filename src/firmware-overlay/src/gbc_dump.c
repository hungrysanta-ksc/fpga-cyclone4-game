/* Exit-only, read-only PSRAM and output SRAM observation. Must follow successful gbc_save_exit.
 * No live polling, memory writes, save-file access, rename or unlink here.
 * Create-new names preserve prior evidence, including incomplete captures.
 */
#include "config.h"
#include "gbc_log_policy.h"
#ifdef GBC_DUMP_G12
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "fileops.h"
#include "memory.h"
#include "gbc_memio.h"
#include "fpga.h"
#include "fpga_spi.h"
#include "crc32.h"
#include "gbc_dump.h"

#define DUMP_BASE 0x800000u
#define INPUT_BYTES 0x72000u
#define OUTPUT_BASE 0x880000u
#define OUTPUT_BYTES 0x10000u
#define CORE_BASE 0xf00000u
#define CORE_BYTES 0x10000u
#define CORE_OFFSET (INPUT_BYTES + OUTPUT_BYTES)
#define DUMP_BYTES (CORE_OFFSET + CORE_BYTES)
#define DUMP_DIR "/sd2snes/gbcdiag/"
static uint8_t dump_armed;
static char dump_rom[192];
static uint32_t boot_snapshot;
static uint8_t boot_snapshot_valid;
static uint8_t dump_block[512];

static void put32(uint8_t *p,uint32_t v) {
  for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));
}
static uint32_t update_crc(uint32_t crc,const uint8_t *p,unsigned n) {
  for(unsigned i=0;i<n;i++)crc=crc32_update(crc,p[i]);
  return crc;
}
void gbc_dump_disarm(void) { dump_armed=0;boot_snapshot_valid=0; }
void gbc_dump_arm(const uint8_t *filename) {
  const char *base=strrchr((const char *)filename,'/');
  base=base?base+1:(const char *)filename;
  strncpy(dump_rom,base,sizeof(dump_rom)-1);
  dump_rom[sizeof(dump_rom)-1]=0;
  dump_armed=1;boot_snapshot_valid=0;
}
/* Called once when reset is requested, BEFORE save exit deasserts RUN.
 * No polling, delay, memory mutation, or disk I/O. D5 holds all four bytes. */
void gbc_dump_observe(void) {
  boot_snapshot_valid=0;
  if(!dump_armed)return;
  uint32_t value=0;
  for(unsigned i=0;i<4;i++) {
    FPGA_SELECT();FPGA_TX_BYTE(0xd5+i);
    uint8_t b=FPGA_RX_BYTE();FPGA_DESELECT();value|=(uint32_t)b<<(8*i);
  }
  boot_snapshot=value;boot_snapshot_valid=(value>>28)==0xc;
}
/* RUN=0 after successful save leaves SRAM output banks intact. The existing
 * boot loader routes MCU 0x880000..0x88ffff to those two 32 KiB banks.
 * No live requests or writes are added; renderer bytes start above 0x890000. */
static uint32_t dump_address(unsigned offset) {
  if(offset>=CORE_OFFSET)return CORE_BASE+offset-CORE_OFFSET;
  return offset<INPUT_BYTES?DUMP_BASE+offset:OUTPUT_BASE+offset-INPUT_BYTES;
}
static uint8_t write_block(FIL *f,uint32_t *crc) {
  UINT n=0;
  if(f_write(f,dump_block,sizeof(dump_block),&n)!=FR_OK||n!=sizeof(dump_block))return 0;
  *crc=update_crc(*crc,dump_block,sizeof(dump_block));
  return 1;
}
uint8_t gbc_dump_exit(void) {
  if(!dump_armed)return 0;
  dump_armed=0; /* Never retry an uncertain diagnostic write automatically. */
  if(fpga_test()!=FPGA_TEST_TOKEN)return 0;
  if(!gbc_file_logs_enabled)return 1; /* Save exit already completed; no SD dump. */
  if(check_or_create_folder(DUMP_DIR)!=FR_OK)return 0;
  FIL f;char path[48];FRESULT res=FR_EXIST;unsigned index;
  for(index=0;index<1000;index++) {
    snprintf(path,sizeof(path),DUMP_DIR "cap%03u.g13d",index);
    res=f_open(&f,(const TCHAR *)path,FA_WRITE|FA_CREATE_NEW);
    if(res!=FR_EXIST)break;
  }
  if(res!=FR_OK)return 0;
  uint32_t file_crc=crc32_init(),first=crc32_init(),second=crc32_init();
  memset(dump_block,0,sizeof(dump_block));
  memcpy(dump_block,"GBDMP04",7);
  put32(dump_block+8,4);put32(dump_block+12,DUMP_BASE);put32(dump_block+16,DUMP_BYTES);
  put32(dump_block+24,0x00090001u); /* packed 9-bit IDs, row streaming */
  put32(dump_block+28,0xafu);
  memcpy(dump_block+32,dump_rom,sizeof(dump_rom));
  put32(dump_block+224,INPUT_BYTES);put32(dump_block+228,OUTPUT_BASE);
  put32(dump_block+232,OUTPUT_BYTES);put32(dump_block+236,INPUT_BYTES);
  if(boot_snapshot_valid) {memcpy(dump_block+240,"BST1",4);put32(dump_block+244,boot_snapshot);}
  memcpy(dump_block+248,"RAM1",4);put32(dump_block+252,CORE_BASE);
  put32(dump_block+256,CORE_BYTES);put32(dump_block+260,CORE_OFFSET);
  uint8_t ok=write_block(&f,&file_crc);
  if(ok)ok=f_sync(&f)==FR_OK; /* Retain header if a later FPGA read times out. */
  for(unsigned off=0;ok&&off<DUMP_BYTES;off+=sizeof(dump_block)) {
    if(gbc_sram_readblock(dump_block,dump_address(off),sizeof(dump_block))!=sizeof(dump_block)){ok=0;break;}
    first=update_crc(first,dump_block,sizeof(dump_block));
    ok=write_block(&f,&file_crc);
  }
  /* A second complete scan detects changes across the capture interval.
   * Matching CRCs are diagnostic evidence, not a proof of physical coherence. */
  for(unsigned off=0;ok&&off<DUMP_BYTES;off+=sizeof(dump_block)) {
    if(gbc_sram_readblock(dump_block,dump_address(off),sizeof(dump_block))!=sizeof(dump_block)){ok=0;break;}
    second=update_crc(second,dump_block,sizeof(dump_block));
  }
  first=crc32_finalize(first);second=crc32_finalize(second);
  if(ok) {
    memset(dump_block,0,sizeof(dump_block));memcpy(dump_block,"GBEND04",7);
    put32(dump_block+8,first);put32(dump_block+12,second);
    put32(dump_block+16,first==second);put32(dump_block+20,index);
    ok=write_block(&f,&file_crc);
  }
  if(ok)ok=f_sync(&f)==FR_OK;
  res=f_close(&f);
  if(!ok||res!=FR_OK)return 0;
  /* Verify the actual file after close; leave failures for offline inspection. */
  if(f_open(&f,(const TCHAR *)path,FA_READ)!=FR_OK)return 0;
  ok=f.fsize==DUMP_BYTES+1024u;
  uint32_t read_crc=crc32_init();
  for(unsigned off=0;ok&&off<DUMP_BYTES+1024u;off+=sizeof(dump_block)) {
    UINT n=0;res=f_read(&f,dump_block,sizeof(dump_block),&n);
    ok=res==FR_OK&&n==sizeof(dump_block);
    if(ok)read_crc=update_crc(read_crc,dump_block,sizeof(dump_block));
  }
  res=f_close(&f);
  return ok&&res==FR_OK&&read_crc==file_crc&&first==second;
}
#endif
