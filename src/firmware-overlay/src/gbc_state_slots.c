#include "config.h"
#include "gbc_state_slots.h"
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "fileops.h"
#include "memory.h"
#include "gbc_memio.h"
#include "crc32.h"
#define STATE_DIR "/sd2snes/gbcstates/"
static uint8_t state_block[512],state_verify[512];
typedef struct { FIL *file; int failed; } state_file_reader;
static int state_read_file(void *p,uint32_t offset,uint8_t *data,uint16_t count) {
 state_file_reader *r=p;UINT got=0;
 if(f_lseek(r->file,offset)!=FR_OK||f_read(r->file,data,count,&got)!=FR_OK||got!=count){r->failed=1;return 0;}
 return 1;
}
static int state_read_stage(void *p,uint32_t offset,uint8_t *data,uint16_t count) {
 uint32_t bytes=*(uint32_t*)p;
 if(offset>bytes||count>bytes-offset)return 0;
 return gbc_sram_readblock(data,GBC_STATE_STAGE_BASE+offset,count)==count;
}
static void state_path(char *path,const gbc_state_identity *id,unsigned bank) {
 /* Bounded numeric names avoid long-name truncation and same-title collisions. */
 snprintf(path,80,STATE_DIR "%08lx-%08lx-%u%c.gst",(unsigned long)id->rom_crc,
  (unsigned long)id->rom_bytes,(unsigned)id->slot+1,bank?'b':'a');
}
/* -1 IO failure, 0 absent/invalid record, 1 fully verified record. */
static int state_inspect(const gbc_state_identity *id,unsigned bank,uint32_t *generation) {
 char path[80];FIL f;state_path(path,id,bank);FRESULT r=f_open(&f,(const TCHAR*)path,FA_READ);
 if(r==FR_NO_FILE||r==FR_NO_PATH)return 0;
 if(r!=FR_OK)return -1;
 state_file_reader reader={&f,0};int ok=gbc_state_validate(state_read_file,&reader,f.fsize,id,generation,0);
 if(f_close(&f)!=FR_OK||reader.failed)return -1;
 return ok;
}
static int state_choose(const gbc_state_identity *id,int *bank,uint32_t *generation) {
 uint32_t a=0,b=0;int va=state_inspect(id,0,&a),vb=state_inspect(id,1,&b);
 if(va<0||vb<0)return 0;
 *bank=-1;*generation=0;
 if(va){*bank=0;*generation=a;}
 if(vb&&(*bank<0||(int32_t)(b-*generation)>0)){*bank=1;*generation=b;}
 return 1;
}
int gbc_state_slot_save(const gbc_state_identity *id) {
 char path[80];uint8_t header[64];FIL f;UINT got;uint32_t generation,total,offset,c;int bank;
 if(!gbc_state_identity_valid(id)||!state_choose(id,&bank,&generation))return 0;
 if(check_or_create_folder(STATE_DIR)!=FR_OK)return 0;
 total=GBC_STATE_CORE_BYTES+id->ram_bytes;c=crc32_init();
 for(offset=0;offset<total;) {
  uint16_t n=(uint16_t)(total-offset>512?512:total-offset);unsigned i;
  if(gbc_sram_readblock(state_block,GBC_STATE_STAGE_BASE+64+offset,n)!=n)return 0;
  if(gbc_sram_readblock(state_verify,GBC_STATE_STAGE_BASE+64+offset,n)!=n||memcmp(state_block,state_verify,n))return 0;
  for(i=0;i<n;i++)c=crc32_update(c,state_block[i]);
  offset+=n;
 }
 if(!gbc_state_header_make(header,id,generation+1,crc32_finalize(c)))return 0;
 bank=bank==0?1:0;state_path(path,id,(unsigned)bank);
 if(f_open(&f,(const TCHAR*)path,FA_WRITE|FA_CREATE_ALWAYS)!=FR_OK)return 0;
 int ok=f_write(&f,header,64,&got)==FR_OK&&got==64;
 for(offset=0;ok&&offset<total;) {
  uint16_t n=(uint16_t)(total-offset>512?512:total-offset);
  ok=gbc_sram_readblock(state_block,GBC_STATE_STAGE_BASE+64+offset,n)==n;
  if(ok)ok=f_write(&f,state_block,n,&got)==FR_OK&&got==n;
  offset+=n;
 }
 if(ok)ok=f_sync(&f)==FR_OK;
 if(f_close(&f)!=FR_OK)ok=0;
 if(!ok)return 0;
 uint32_t checked=0;
 return state_inspect(id,(unsigned)bank,&checked)==1&&checked==generation+1;
}
int gbc_state_slot_stage_load(const gbc_state_identity *id) {
 char path[80];FIL f;UINT got;uint32_t generation,total,offset;int bank;
 if(!gbc_state_identity_valid(id)||!state_choose(id,&bank,&generation)||bank<0)return 0;
 state_path(path,id,(unsigned)bank);
 if(f_open(&f,(const TCHAR*)path,FA_READ)!=FR_OK)return 0;
 total=64+GBC_STATE_CORE_BYTES+id->ram_bytes;
 int ok=f.fsize==total;
 for(offset=0;ok&&offset<total;) {
  uint16_t n=(uint16_t)(total-offset>512?512:total-offset);
  ok=f_read(&f,state_block,n,&got)==FR_OK&&got==n;
  if(ok)ok=gbc_sram_writeblock(state_block,GBC_STATE_STAGE_BASE+offset,n)==n;
  if(ok)ok=gbc_sram_readblock(state_verify,GBC_STATE_STAGE_BASE+offset,n)==n&&!memcmp(state_block,state_verify,n);
  offset+=n;
 }
 if(f_close(&f)!=FR_OK)ok=0;
 if(!ok)return 0;
 uint32_t checked=0;
 return gbc_state_validate(state_read_stage,&total,total,id,&checked,0)&&checked==generation;
}
