/* Dedicated GBC snapshot/exit persistence. No stock SNES hooks or live CRC scan.
 * Raw SRM uses the cartridge RAM size (512 bytes through 128KiB). Temporary writes never truncate the
 * current save; the previous committed file survives the rename window.
 * This mitigates interrupted writes, not filesystem-wide power-loss damage.
 */
#include "config.h"
#ifdef GBC_SAVE_G12
#include <string.h>
#include "ff.h"
#include "fileops.h"
#include "memory.h"
#include "fpga.h"
#include "fpga_spi.h"
#include "snes.h"
#include "timer.h"
#include "led.h"
#include "crc32.h"
#include "gbc_save.h"
#include "gbc_memio.h"
#include "rtc.h"
#include "gbc_rtc_codec.h"


#define SAVE_BLOCK 512u
static uint8_t snapshot[SAVE_BLOCK], verify[SAVE_BLOCK];
static char save_path[256], temp_path[256], previous_path[256];
static uint8_t armed, captured, recovered;
static uint8_t autosave_enabled=1;
static uint8_t rtc_upgrade,rtc_captured,has_rtc,rtc_footer[48],loaded_rtc[48];
static uint64_t rtc_snapshot_time;
static int rtc_utc_minutes;
static int rtc_read_timezone(void) {
 /* FXPAK stores local civil time. User-visible setting gives its UTC offset. */
 FIL f;UINT n=0;char b[12]={0};rtc_utc_minutes=0;
 FRESULT r=f_open(&f,(const TCHAR *)"/sd2snes/gbc-utc-offset.txt",FA_READ);
 if(r==FR_NO_FILE||r==FR_NO_PATH)return 1;
 if(r!=FR_OK)return 0;
 int ok=f.fsize>0&&f.fsize<sizeof(b)&&f_read(&f,b,sizeof(b)-1,&n)==FR_OK&&n==f.fsize;
 if(f_close(&f)!=FR_OK)ok=0;
 if(!ok)return 0;
 unsigned i=0;int sign=1,x=0;if(b[i]=='-'||b[i]=='+'){if(b[i]=='-')sign=-1;i++;}
 unsigned start=i;while(i<n&&b[i]>='0'&&b[i]<='9'){x=x*10+b[i++]-'0';if(x>840)return 0;}
 if(i==start)return 0;
 while(i<n&&(b[i]=='\r'||b[i]=='\n'||b[i]==' '))i++;
 if(i!=n||sign*x < -720)return 0;
 rtc_utc_minutes=sign*x;return 1;
}
static int rtc_now(uint64_t *out) {
 struct tm t;if(!rtc_isvalid())return 0;read_rtc(&t);
 if(t.tm_year<1970||t.tm_year>9999||t.tm_mon<1||t.tm_mon>12||!t.tm_mday||t.tm_mday>31||t.tm_hour>23||t.tm_min>59||t.tm_sec>59)return 0;
 uint64_t epoch=gbc_rtc_epoch(t.tm_year,t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min,t.tm_sec);
 if(rtc_utc_minutes>0&&epoch<(unsigned)rtc_utc_minutes*60u)return 0;
 *out=epoch-(int64_t)rtc_utc_minutes*60;return 1;
}
static int rtc_install(const uint8_t *b,unsigned n) {
 uint64_t now;uint8_t regs[10],verify_regs[10],ignored,copy_latch=0;
 if(!rtc_now(&now)||!gbc_rtc_decode(regs,b,n,now))return 0;
 if((gbc_sram_writeblock(regs+5,0xf20000,5)!=5||gbc_sram_writeblock(&copy_latch,0xf2000e,1)!=1||gbc_sram_writeblock(regs,0xf20000,5)!=5)||gbc_sram_readblock(&ignored,0xf2000f,1)!=1||(gbc_sram_readblock(verify_regs,0xf20000,5)!=5||gbc_sram_readblock(verify_regs+5,0xf20008,5)!=5))return 0;
 /* The live seconds can tick during readback; installation restarts the divider. */
 if(memcmp(regs,verify_regs,10))return 0;
 memset(loaded_rtc,0,48);if(n)memcpy(loaded_rtc,b,n);rtc_upgrade=n!=48;
 return 1;
}
static int rtc_capture(void) {
 uint8_t regs[10],check[10];
 for(unsigned retry=0;retry<4;retry++){
  if(!rtc_now(&rtc_snapshot_time))return 0;
  if(gbc_sram_readblock(regs,0xf20000,5)!=5||gbc_sram_readblock(regs+5,0xf20008,5)!=5||
     gbc_sram_readblock(check,0xf20000,5)!=5||gbc_sram_readblock(check+5,0xf20008,5)!=5)return 0;
  if(!memcmp(regs,check,10)){gbc_rtc_encode(rtc_footer,regs,rtc_snapshot_time);return 1;}
 }
 return 0;
}

static uint32_t save_bytes, loaded_crc, captured_crc;
#define SNAPSHOT_BASE 0xe20000u
static uint32_t capture_base=SRAM_SAVE_ADDR;
static uint8_t commit_phase,auto_dirty,auto_snapshot,auto_error;
static uint32_t committed_generation,seen_generation,snapshot_generation;
static tick_t auto_poll_tick,auto_first_tick,auto_change_tick,auto_retry_tick;
static uint8_t commit_save(void);

static uint32_t block_crc(uint32_t crc,const uint8_t *data) {
  for(unsigned i=0;i<SAVE_BLOCK;i++) crc=crc32_update(crc,data[i]);
  return crc;
}
void gbc_save_disarm(void) { armed=0;captured=0;recovered=0;save_bytes=0;has_rtc=0;rtc_captured=0;
  capture_base=SRAM_SAVE_ADDR;commit_phase=auto_dirty=auto_snapshot=auto_error=0;
  committed_generation=seen_generation=snapshot_generation=0;
  auto_poll_tick=auto_first_tick=auto_change_tick=auto_retry_tick=getticks(); }

/* 1 valid, 0 absent, -1 malformed/IO. Loading never changes SD files.
 * The core remains stopped until the complete file has been verified. */
static int read_save(const char *path) {
  FIL file;
  FRESULT res=f_open(&file,(const TCHAR *)path,FA_READ);
  if(res==FR_NO_FILE || res==FR_NO_PATH) return 0;
  if(res!=FR_OK) return -1;
  unsigned tail=file.fsize>=save_bytes?file.fsize-save_bytes:1;
  uint8_t ok=tail==0||(has_rtc&&(tail==44||tail==48));
  uint32_t crc=crc32_init();
  for(unsigned offset=0;ok && offset<save_bytes;offset+=SAVE_BLOCK) {
    UINT count=0;
    res=f_read(&file,snapshot,SAVE_BLOCK,&count);
    ok=res==FR_OK && count==SAVE_BLOCK;
    if(!ok) break;
    sram_writeblock(snapshot,SRAM_SAVE_ADDR+offset,SAVE_BLOCK);
    sram_readblock(verify,SRAM_SAVE_ADDR+offset,SAVE_BLOCK);
    ok=!memcmp(snapshot,verify,SAVE_BLOCK);
    crc=block_crc(crc,snapshot);
  }
  if(ok&&has_rtc){
    uint8_t footer[48]={0};UINT n=0;
    if(tail&&(f_read(&file,footer,tail,&n)!=FR_OK||n!=tail))ok=0;
    if(ok&&!rtc_install(footer,tail))ok=0;
  }
  res=f_close(&file);
  if(!ok || res!=FR_OK) return -1;
  loaded_crc=crc32_finalize(crc);
  return 1;
}
static uint8_t build_paths(const uint8_t *filename) {
  const char *base=strrchr((const char *)filename,'/');
  base=base ? base+1 : (const char *)filename;
  const char *dot=strrchr(base,'.');
  if(!dot || dot==base) return 0;
  size_t prefix=strlen(SAVE_BASEDIR), stem=(size_t)(dot-base);
  /* Reserve the longest suffix, including NUL; no silent truncation/collision. */
  if(prefix+stem+sizeof(".srm.gbc-prev")>sizeof(save_path)) return 0;
  memcpy(save_path,SAVE_BASEDIR,prefix);
  memcpy(save_path+prefix,base,stem);
  strcpy(save_path+prefix+stem,".srm");
  strcpy(temp_path,save_path); strcat(temp_path,".gbc-tmp");
  strcpy(previous_path,save_path); strcat(previous_path,".gbc-prev");
  return 1;
}


uint8_t gbc_save_load(const uint8_t *rom_filename,uint32_t size,uint8_t timer) {
  gbc_save_disarm();
  if(size!=0 && size!=512 && size!=2048 && size!=8192 && size!=32768 &&
     size!=65536 && size!=131072) return 0;
  save_bytes=size;has_rtc=!!timer;
  if(has_rtc&&!rtc_read_timezone())return 0;
  /* No-RAM games participate in the exit lifecycle without any save-file I/O. */
  if(!size&&!has_rtc) { armed=1;return 1; }
  if(!build_paths(rom_filename)) return 0;
  int current=read_save(save_path);
  if(current<0) return 0;
  if(!current) {
    int previous=read_save(previous_path);
    if(previous<0) return 0;
    if(previous) recovered=1;
    else {
      uint32_t crc=crc32_init();
      memset(snapshot,0xff,sizeof(snapshot));
      for(unsigned offset=0;offset<save_bytes;offset+=SAVE_BLOCK) {
        sram_writeblock(snapshot,SRAM_SAVE_ADDR+offset,SAVE_BLOCK);
        sram_readblock(verify,SRAM_SAVE_ADDR+offset,SAVE_BLOCK);
        if(memcmp(snapshot,verify,SAVE_BLOCK)) return 0;
        crc=block_crc(crc,snapshot);
      }
      loaded_crc=crc32_finalize(crc);
      if(has_rtc&&!rtc_install(0,0))return 0;
    }
  }
  armed=1;
  return 1;
}

/* Frozen PSRAM retains the full snapshot; MCU RAM holds only two blocks.
 * Compare repeated reads and bind every subsequent pass to captured_crc. */
static uint8_t capture_save(void) {
  if(has_rtc&&!rtc_captured){if(!rtc_capture())return 0;rtc_captured=1;}
  uint32_t crc=crc32_init();
  for(unsigned offset=0;offset<save_bytes;offset+=SAVE_BLOCK) {
    sram_readblock(snapshot,capture_base+offset,SAVE_BLOCK);
    sram_readblock(verify,capture_base+offset,SAVE_BLOCK);
    if(memcmp(snapshot,verify,SAVE_BLOCK)) return 0;
    crc=block_crc(crc,snapshot);
  }
  uint32_t value=crc32_finalize(crc);
  if(captured && value!=captured_crc) return 0;
  captured_crc=value;captured=1;
  return 1;
}
static uint8_t verify_file(const char *path) {
  FIL file;
  FRESULT res=f_open(&file,(const TCHAR *)path,FA_READ);
  if(res!=FR_OK) return 0;
  uint8_t ok=file.fsize==save_bytes+(has_rtc?48u:0u);
  uint32_t crc=crc32_init();
  for(unsigned offset=0;ok && offset<save_bytes;offset+=SAVE_BLOCK) {
    UINT count=0;
    res=f_read(&file,verify,SAVE_BLOCK,&count);
    sram_readblock(snapshot,capture_base+offset,SAVE_BLOCK);
    ok=res==FR_OK && count==SAVE_BLOCK && !memcmp(snapshot,verify,SAVE_BLOCK);
    crc=block_crc(crc,snapshot);
  }
  if(ok&&has_rtc){uint8_t b[48];UINT n=0;if(f_read(&file,b,48,&n)!=FR_OK||n!=48||memcmp(b,rtc_footer,48))ok=0;}
  res=f_close(&file);
  return ok && res==FR_OK && crc32_finalize(crc)==captured_crc;
}
static uint8_t write_temporary(void) {
  FIL file;
  FRESULT res=f_open(&file,(const TCHAR *)temp_path,FA_WRITE|FA_CREATE_ALWAYS);
  if(res!=FR_OK) return 0;
  uint8_t ok=1;
  uint32_t crc=crc32_init();
  for(unsigned offset=0;ok && offset<save_bytes;offset+=SAVE_BLOCK) {
    UINT count=0;
    sram_readblock(snapshot,capture_base+offset,SAVE_BLOCK);
    sram_readblock(verify,capture_base+offset,SAVE_BLOCK);
    if(memcmp(snapshot,verify,SAVE_BLOCK)) { ok=0;break; }
    crc=block_crc(crc,snapshot);
    res=f_write(&file,snapshot,SAVE_BLOCK,&count);
    ok=res==FR_OK && count==SAVE_BLOCK;
  }
  if(ok) ok=crc32_finalize(crc)==captured_crc;
  if(ok&&has_rtc){UINT n=0;if(f_write(&file,rtc_footer,48,&n)!=FR_OK||n!=48)ok=0;}
  if(ok) ok=f_sync(&file)==FR_OK;
  res=f_close(&file);
  return ok && res==FR_OK && verify_file(temp_path);
}
/* Retain rename progress across retries; never rotate an unverified new
 * canonical file over the previous committed image after an I/O failure. */
static uint8_t commit_save(void) {
  if(!commit_phase) {
    if(!recovered && captured_crc==loaded_crc&&(!has_rtc||(!rtc_upgrade&&!memcmp(rtc_footer,loaded_rtc,48))))return 1;
    if(check_or_create_folder(SAVE_BASEDIR)!=FR_OK || !write_temporary())return 0;
    commit_phase=1;
  }
  if(commit_phase==1) {
    FILINFO info;memset(&info,0,sizeof(info));
    FRESULT res=f_stat((const TCHAR *)save_path,&info);
    if(res==FR_OK) {
      res=f_unlink((const TCHAR *)previous_path);
      if(res!=FR_OK && res!=FR_NO_FILE)return 0;
      if(f_rename((const TCHAR *)save_path,(const TCHAR *)previous_path)!=FR_OK)return 0;
    } else if(res!=FR_NO_FILE && res!=FR_NO_PATH)return 0;
    commit_phase=2;
  }
  if(commit_phase==2) {
    if(f_rename((const TCHAR *)temp_path,(const TCHAR *)save_path)!=FR_OK)return 0;
    commit_phase=3;
  }
  if(!verify_file(save_path))return 0;
  loaded_crc=captured_crc;rtc_upgrade=0;if(has_rtc)memcpy(loaded_rtc,rtc_footer,48);recovered=0;commit_phase=0;
  return 1;
}
static uint8_t save_command(uint8_t command) {
  FPGA_SELECT();FPGA_TX_BYTE(command);uint8_t value=FPGA_RX_BYTE();FPGA_DESELECT();return value;
}
static uint32_t save_generation_read(uint8_t command) {
  uint32_t value=0;
  for(unsigned i=0;i<4;i++)value|=(uint32_t)save_command(command+i)<<(8*i);
  return value;
}
static uint8_t live_snapshot(void) {
  if(has_rtc&&!rtc_now(&rtc_snapshot_time))return 0;
  (void)save_command(0xdd);
  tick_t start=getticks();
  do {
    uint8_t status=save_command(0xde);
    if((status&0xf8)!=0xa8 || (status&4))return 0;
    if(!(status&1) && (status&2)) {
      if(has_rtc){
        uint8_t b;rtc_captured=0;
        int ok=rtc_now(&rtc_snapshot_time)&&rtc_capture()&&save_command(0xde)==0xaa;
        int released=gbc_sram_readblock(&b,0xf2000f,1)==1;
        if(!ok||!released)return 0;
        rtc_captured=1;
      }
      snapshot_generation=save_generation_read(0xe0);
      capture_base=SNAPSHOT_BASE;captured=0;auto_snapshot=1;
      return 1;
    }
    delay_ms(1);
  } while((tick_t)(getticks()-start)<MS_TO_TICKS(250));
  /* The independent FPGA watchdog releases its pause even if SPI fails. */
  return 0;
}
void gbc_save_poll(void) {
  if(!armed || (!save_bytes&&!has_rtc) || (!autosave_enabled&&!auto_snapshot))return;
  tick_t now=getticks();
  if(auto_error){writeled((now/25)&1);readled(!((now/25)&1));}
  if((tick_t)(now-auto_poll_tick)<MS_TO_TICKS(100))return;
  auto_poll_tick=now;
  if(auto_error && (tick_t)(now-auto_retry_tick)<MS_TO_TICKS(2000))return;
  if(!auto_snapshot) {
    uint32_t generation=save_generation_read(0xd9);
    if(generation==committed_generation && !recovered)return;
    if(!auto_dirty){auto_dirty=1;auto_first_tick=auto_change_tick=now;}
    if(generation!=seen_generation){seen_generation=generation;auto_change_tick=now;}
    if((tick_t)(now-auto_change_tick)<MS_TO_TICKS(1000) &&
       (tick_t)(now-auto_first_tick)<MS_TO_TICKS(5000))return;
    writeled(1);readled(0);
    if(!live_snapshot())goto error;
  }
  writeled(1);readled(0);
  if(!captured && !capture_save())goto error;
  if(!commit_save())goto error;
  committed_generation=snapshot_generation;
  auto_snapshot=auto_dirty=auto_error=0;captured=0;rtc_captured=0;
  capture_base=SRAM_SAVE_ADDR;writeled(0);readled(0);
  return;
error:
  auto_error=1;auto_retry_tick=getticks();writeled(1);
}
void gbc_save_set_auto(uint8_t enable) { autosave_enabled=!!enable; }
uint8_t gbc_save_status(void) { return (auto_error?8:0)|(!save_bytes&&!has_rtc?16:0); }
uint8_t gbc_save_now(void) {
  if(!armed)return 0;
  if(!save_bytes&&!has_rtc)return 1;
  writeled(1);readled(0);
  /* A failed older transaction must finish before its held image is replaced. */
  if(auto_snapshot) {
    if((!captured && !capture_save()) || !commit_save())goto fail;
    auto_snapshot=0;captured=0;
  }
  if(!live_snapshot() || !capture_save() || !commit_save())goto fail;
  committed_generation=snapshot_generation;
  auto_snapshot=auto_dirty=auto_error=0;captured=0;rtc_captured=0;capture_base=SRAM_SAVE_ADDR;
  writeled(0);readled(0);return 1;
fail:
  auto_error=1;auto_retry_tick=getticks();return 0;
}
uint8_t gbc_save_exit(void) {
  snes_reset(1);fpga_set_chipfeat(0);delay_ms(20);
  if(!armed || fpga_test()!=FPGA_TEST_TOKEN)return 0;
  if(!save_bytes&&!has_rtc)return 1;
  /* Finish any interrupted SD transaction against the held shadow first.
   * Then capture current live RAM, including changes made during that write. */
  if(auto_snapshot) {
    if(!captured && !capture_save())return 0;
    if(!commit_save())return 0;
    auto_snapshot=0;captured=0;capture_base=SRAM_SAVE_ADDR;
  }
  if(has_rtc&&!captured){rtc_captured=0;if(!rtc_now(&rtc_snapshot_time))return 0;}
  if(!capture_save())return 0;
  return commit_save();
}
/* Finish only an already captured transaction. A state load does not itself
 * request a new battery-save write before replacing live cartridge RAM. */
uint8_t gbc_save_before_state_load(void) {
 if(!armed)return 0;
 if(auto_snapshot) {
  if((!captured&&!capture_save())||!commit_save())return 0;
  committed_generation=snapshot_generation;
 }
 auto_snapshot=auto_dirty=auto_error=0;captured=0;rtc_captured=0;capture_base=SRAM_SAVE_ADDR;
 return 1;
}
void gbc_save_after_state_load(void) {
 uint32_t generation=save_generation_read(0xd9);
 /* MCU state writes bypass the CPU dirty counter. Force one normal autosave
  * comparison, retaining loaded_crc as the actual on-disk baseline. */
 committed_generation=generation-1;seen_generation=generation;
 auto_snapshot=auto_dirty=auto_error=0;captured=0;rtc_captured=0;capture_base=SRAM_SAVE_ADDR;
 auto_poll_tick=auto_first_tick=auto_change_tick=auto_retry_tick=getticks();
}
#endif
