#include "config.h"
#include "gbc_state_transfer.h"
#include "gbc_state_slots.h"
#include "memory.h"
#include "gbc_memio.h"
#include "timer.h"
#include "gbc_save.h"
#include <string.h>
#define STATE_CONTROL 0xf10801u
#define STATE_IO_STATUS 0xf10800u
static uint8_t block[512],verify[512];
static uint8_t fatal;
static uint32_t trace_step,trace_address,trace_control,trace_io;
void gbc_state_diagnostic(uint32_t out[4]){out[0]=trace_step;out[1]=trace_address;out[2]=trace_control;out[3]=trace_io;}
static void trace_begin(unsigned step){trace_step=step;trace_address=0;trace_control=trace_io=0xff;gbc_memio_clear_error();}
int gbc_state_faulted(void) { return fatal; }
/* Only called after FPGA/core reload, never to escape an incomplete restore. */
void gbc_state_reset_session(void) { fatal=0; }
static int control(uint8_t command) { return gbc_sram_writeblock(&command,STATE_CONTROL,1)==1; }
static int wait_status(uint8_t mask,uint8_t expected) {
 tick_t start=getticks();
 do {
  uint8_t value=0xff;
  if(gbc_sram_readblock(&value,STATE_CONTROL,1)!=1)return 0;
  trace_control=value;if(value&0x80)return 0;
  if((value&mask)==expected)return 1;
  delay_ms(1);
 } while((tick_t)(getticks()-start)<MS_TO_TICKS(250));
 return 0;
}
static int io_ok(void) {
 uint8_t value=0xff;
 int ok=gbc_sram_readblock(&value,STATE_IO_STATUS,1)==1;trace_io=value;return ok&&value==1;
}
static int clear_io(void) {
 uint8_t value=0;
 return gbc_sram_writeblock(&value,STATE_IO_STATUS,1)==1&&io_ok();
}
static int failed_locked(void) { fatal=1;gbc_save_disarm();return -1; }
static int release_capture(int result) {
 uint32_t prior_control=trace_control;
 if(!control(0)||!wait_status(4,0))return failed_locked();
 if(!result)trace_control=prior_control;
 return result;
}
int gbc_state_capture(const gbc_state_identity *id) {
 uint32_t off=0,total,address;
 trace_begin(1);
 if(fatal||!gbc_state_identity_valid(id))return fatal?-1:0;
 trace_step=2;
 if(!control(1)||!wait_status(0x1f,5))return release_capture(0);
 trace_step=3;
 if(!clear_io())return release_capture(0);
 total=GBC_STATE_CORE_BYTES+id->ram_bytes;
 while(off<total) {
  uint16_t n=gbc_state_region(off,id->ram_bytes,sizeof(block),&address);
  trace_step=4;trace_address=address;
  if(!n||gbc_sram_readblock(block,address,n)!=n||gbc_sram_readblock(verify,address,n)!=n||memcmp(block,verify,n))return release_capture(0);
  trace_step=5;trace_address=GBC_STATE_STAGE_BASE+64+off;
  if(gbc_sram_writeblock(block,GBC_STATE_STAGE_BASE+64+off,n)!=n||
     gbc_sram_readblock(verify,GBC_STATE_STAGE_BASE+64+off,n)!=n||memcmp(block,verify,n))return release_capture(0);
  off+=n;
 }
 trace_step=6;
 if(!io_ok())return release_capture(0);
 trace_step=7;int released=release_capture(1);if(released!=1)return released;
 trace_step=8;int saved=gbc_state_slot_save(id);if(saved)trace_step=9;return saved;
}
/* Validate the complete live image after all register commits, including
 * side effects a later commit could have had on an earlier register. */
static int read_restored(void *context,uint32_t offset,uint8_t *data,uint16_t count) {
 const gbc_state_identity *id=context;
 while(count) {
  uint32_t address;uint16_t n;
  if(offset<64) {n=(uint16_t)(64-offset);if(n>count)n=count;address=GBC_STATE_STAGE_BASE+offset;}
  else n=gbc_state_region(offset-64,id->ram_bytes,count,&address);
  if(!n||gbc_sram_readblock(data,address,n)!=n)return 0;
  data+=n;offset+=n;count-=n;
 }
 return 1;
}
int gbc_state_restore(const gbc_state_identity *id) {
 uint32_t off=0,total,address;
 trace_begin(20);
 if(fatal||!gbc_state_identity_valid(id))return fatal?-1:0;
 /* Full file + staged-copy validation precedes the first live write. */
 if(!gbc_state_slot_stage_load(id)||!gbc_save_before_state_load())return 0;
 trace_step=22;
 if(!control(2)||!wait_status(0x1f,0x1d)||!clear_io())return failed_locked();
 total=GBC_STATE_CORE_BYTES+id->ram_bytes;
 while(off<total) {
  uint16_t n=gbc_state_region(off,id->ram_bytes,sizeof(block),&address);
  trace_step=23;trace_address=GBC_STATE_STAGE_BASE+64+off;
  if(!n||gbc_sram_readblock(block,GBC_STATE_STAGE_BASE+64+off,n)!=n||
     gbc_sram_readblock(verify,GBC_STATE_STAGE_BASE+64+off,n)!=n||memcmp(block,verify,n))return failed_locked();
  trace_step=24;trace_address=address;
  if(gbc_sram_writeblock(block,address,n)!=n||gbc_sram_readblock(verify,address,n)!=n||memcmp(block,verify,n))return failed_locked();
  off+=n;
 }
 trace_step=25;
 if(!gbc_state_validate(read_restored,(void*)id,64+total,id,0,0)||!io_ok()||!control(3)||!wait_status(0x5f,0x4d))return failed_locked();
 /* Synchronize autosave bookkeeping while the restored core is still held. */
 trace_step=27;gbc_save_after_state_load();
 trace_step=28;
 if(!control(0)||!wait_status(4,0))return failed_locked();
 trace_step=29;return 1;
}
