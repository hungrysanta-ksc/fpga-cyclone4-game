/* SPDX-License-Identifier: GPL-2.0-only */
/* Hardware seams only. Actual boot, checkpoint and report are linked. */
#include "config.h"
#include "nes_report_boot080.h"
#include "rle.h"
#include "cfgware.h"
#include "snesboot.h"
struct fake_nvic nvic;
int snes_boot_configured,file_status;
const uint8_t *fpga_config;
uint8_t gbc_spi_pacing;
static unsigned held,prog,configured,sent,postinit,io,atfault,atcorrupt;
static unsigned marker_mask,marker_delay_fail,pinfault;
static unsigned display_ticks,delay_stage,release_mask,init_commands,high_capacity;
static unsigned init_delays,fail_delay,slow_clock,stage_tick_cost;
static uint8_t rom[65535],screen[24*33],golden_mini[153544],golden_boot[65535];
bool report_session084(void);
static bool row(unsigned line,const char *s){
 const uint8_t *p=screen+line*33;unsigned n=(unsigned)strlen(s);
 assert(n<=26&&!p[32]);
 for(unsigned i=0;i<32;i++){
  uint8_t want=i>=(32-n)/2&&i<(32-n)/2+n?(uint8_t)s[i-(32-n)/2]:' ';
  if(p[i]!=want)printf("row expected '%s' received '%s'\n",s,p);
  assert(p[i]==want);
 }
 return true;
}
void snes_reset(int n){
 if(!n){
  assert(!nes_return_failed()&&snes_boot_configured&&!nvic.ISER[2]);
  assert(stage>=1&&stage<=9);release_mask|=1u<<stage;
  if(stage==1){
   assert(!nes_return_log_allowed());
   if(!init_commands){assert(marker_mask==0&&row(8,"STEP 1A INIT SD"));marker_mask=1;}
   else if(marker_mask==1){assert(!commands&&init_commands==17&&row(8,"STEP 1B MOUNT FAT"));marker_mask=3;}
   else{assert(marker_mask==3&&commands&&fatfs.fs_type&&row(8,"STEP 1C FIND SPACE"));marker_mask=7;}
  }else if(stage<9)assert(nes_return_log_allowed());else assert(!nes_return_log_allowed());
 }
 held=(unsigned)n;
}
uint8_t get_snes_reset(void){return (uint8_t)held;}
void nes_diag_blocked(void){assert(held);abort();}
void fpga_init(void){assert(held&&!nes_return_failed()&&!commands&&!init_commands&&!fatfs.fs_type);}
void fpga_set_prog_b(uint8_t n){assert(!nes_return_failed());prog=n;}
unsigned read_prog(void){return pinfault==1?1:prog;}
int fpga_get_initb(void){return pinfault==2?0:(int)prog;}
int fpga_get_done(void){return pinfault==3?1:pinfault==4?0:sent==153544;}
void send_byte(uint8_t n){assert(held&&!nes_return_failed()&&sent<153544&&n==golden_mini[sent]);sent++;}
void fpga_postinit(void){assert(sent==153544);postinit++;configured=1;}
bool nes_return_delay(unsigned n,bool ms){
 assert(!nes_return_failed());
 if(!ms){assert(n==2&&held&&stage==1);assert(marker_mask==1);init_delays++;
  if(init_delays==fail_delay){nes_return_fail(NES_DIAG_TIMER);return false;}
  if(slow_clock)display_ticks++;
 }else if(n==1000){
  assert(stage==1&&!held&&!nes_return_log_allowed());
  if(marker_delay_fail==marker_mask){nes_return_fail(NES_DIAG_TIMER);return false;}
  display_ticks+=100;
 }else if(n==1){assert(held&&sent==153544);}
 else{
  assert(n==500&&!held&&stage>=2&&stage<=8);
  assert(strstr((char *)screen+8*33,"STEP "));
  if(stage==delay_stage){nes_return_fail(NES_DIAG_TIMER);return false;}
  display_ticks+=stage_tick_cost?stage_tick_cost:50;
 }
 return true;
}
static bool touch(void){
 assert(held&&configured&&!nes_return_failed()&&!nvic.ISER[2]);io++;
 if(io==atfault){nes_return_fail(NES_DIAG_SPI);return false;}return true;
}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){
 if(!touch())return n;
 if(a>=0xff1000){assert(a+n<=0xff1000+sizeof(screen));
  assert(n==33);const uint8_t *b=p;assert(!b[32]);
  for(unsigned i=0;i<3;i++)assert(b[i]==' '&&b[31-i]==' ');
  memcpy(screen+a-0xff1000,p,n);}
 else{assert(a>=0xc00000&&a+n<=0xc00000+sizeof(rom));memcpy(rom+a-0xc00000,p,n);}
 return n;
}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){
 if(!touch())return n;
 if(a>=0xff1000)memcpy(p,screen+a-0xff1000,n);else memcpy(p,rom+a-0xc00000,n);
 if(io==atcorrupt)((uint8_t *)p)[0]^=1;
 return n;
}
void set_saveram_mask(uint32_t x){assert(x==0x1fff);(void)touch();}
void set_rom_mask(uint32_t x){assert(x==0x3fffff);(void)touch();}
void set_mapper(uint8_t x){assert(x==7);(void)touch();}
uint8_t file_getc(void){assert(0);return 0;}
static unsigned legacy(const uint8_t *s,unsigned size,uint8_t *out,unsigned limit){
 unsigned n=0;rle_mem_init(s,size);for(;;){uint8_t b=rle_mem_getc();if(rle_state)break;assert(n<limit);out[n++]=b;}return n;
}
