#include "config.h"
#ifdef GBC_SAVE_G12
#include <stdint.h>
#include <string.h>
#include "ff.h"
#include "fileops.h"
#include "fpga_spi.h"
#include "crc32.h"
#include "gbc_save.h"
#include "gbc_menu.h"
#include "gbc_state_transfer.h"
#include "gbc_state_report.h"
static gbc_state_identity state_identity;
void gbc_menu_bind_state(uint32_t bytes,uint32_t crc,uint32_t ram) {
 state_identity=(gbc_state_identity){bytes,crc,ram,0};gbc_state_reset_session();
}

/* Two independent records; never truncate the newest valid record. */
static const char *paths[2]={"/sd2snes/gbc-settings0.dat","/sd2snes/gbc-settings1.dat"};
static uint8_t options=1,menu_open,settings_error;
static uint8_t reset_prepared,reset_requested;
static int active=-1;
static uint32_t sequence;
static uint32_t get32(const uint8_t *p) { return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static void put32(uint8_t *p,uint32_t x) { for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(x>>(8*i)); }
static uint32_t checksum(const uint8_t *p) {
  uint32_t c=crc32_init();for(unsigned i=0;i<12;i++)c=crc32_update(c,p[i]);return crc32_finalize(c);
}
static int read_record(int slot,uint8_t *b) {
  FIL f;UINT count=0;FRESULT r=f_open(&f,(const TCHAR *)paths[slot],FA_READ);
  if(r==FR_NO_FILE || r==FR_NO_PATH)return 0;
  if(r!=FR_OK)return -1;
  int ok=f.fsize==16 && f_read(&f,b,16,&count)==FR_OK && count==16;
  if(f_close(&f)!=FR_OK)ok=0;
  return ok && !memcmp(b,"GC29",4) && b[4]==1 && !(b[5]&~3) &&
    (b[6]^b[5])==255 && b[7]==0 && get32(b+12)==checksum(b) ? 1 : -1;
}
static uint8_t persist(uint8_t value) {
  uint8_t b[16]={'G','C','2','9',1,value,(uint8_t)~value,0},check[16];
  int slot=active==0?1:0;put32(b+8,sequence+1);put32(b+12,checksum(b));
  FIL f;UINT count=0;
  if(f_open(&f,(const TCHAR *)paths[slot],FA_CREATE_ALWAYS|FA_WRITE)!=FR_OK)return 0;
  uint8_t ok=f_write(&f,b,16,&count)==FR_OK && count==16;
  if(ok && f_sync(&f)!=FR_OK)ok=0;
  if(f_close(&f)!=FR_OK)ok=0;
  if(!ok || read_record(slot,check)!=1 || memcmp(b,check,16))return 0;
  active=slot;sequence++;options=value;settings_error=0;return 1;
}
static void respond(uint8_t result) {
  uint8_t value=(menu_open?128:0)|options|(settings_error?4:0)|gbc_save_status()|result;
  FPGA_SELECT();FPGA_TX_BYTE(0xe5);FPGA_TX_BYTE(value);FPGA_DESELECT();
}
void gbc_menu_begin(void) {
  uint8_t a[16],b[16];int ra=read_record(0,a),rb=read_record(1,b);
  active=-1;sequence=0;options=1;menu_open=0;settings_error=0;reset_prepared=reset_requested=0;
  if(ra==1) {active=0;sequence=get32(a+8);options=a[5];}
  if(rb==1 && (active<0 || (int32_t)(get32(b+8)-sequence)>0)) {
    active=1;sequence=get32(b+8);options=b[5];
  }
  if(active<0 && (ra<0 || rb<0))settings_error=1;
  gbc_save_set_auto(options&1);respond(0);
}
void gbc_menu_poll(void) {
  FPGA_SELECT();FPGA_TX_BYTE(0xe4);uint8_t command=FPGA_RX_BYTE();FPGA_DESELECT();
  if(!command)return;
  if(command!=7)reset_prepared=0;
  uint8_t result=0;
  switch(command) {
   case 1:menu_open=1;break;
   case 2:
    if(!menu_open || !gbc_save_now())result=64;
    else result=32;
    break;
   case 3:case 4:
    if(!menu_open)result=64;
    else if(!persist(options^(command==3?1:2))) {settings_error=1;result=64;}
    gbc_save_set_auto(options&1);break;
   case 5:if(gbc_state_faulted())result=64;else menu_open=0;break;
   case 6:
    if(!menu_open || (!gbc_state_faulted()&&!gbc_save_now()))result=64;
    else reset_prepared=1;
    break;
   case 7:
    if(!menu_open || !reset_prepared)result=64;
    else {reset_requested=1;reset_prepared=0;}
    break;
   default:
    if(menu_open&&((command>=0x10&&command<=0x13)||(command>=0x20&&command<=0x23))) {
      state_identity.slot=command&3;
      int ok=command<0x20?gbc_state_capture(&state_identity):gbc_state_restore(&state_identity);
      gbc_state_report(&state_identity,command,ok);
      result=ok==1?32:64;
    } else result=64;
    break;
  }
  respond(result);
}
uint8_t gbc_menu_take_reset(void) { uint8_t r=reset_requested;reset_requested=0;return r; }
#endif
