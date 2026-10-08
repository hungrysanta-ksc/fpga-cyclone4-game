/* SPDX-License-Identifier: MIT */
/* Main/load_rom execute verbatim; RTC/CIC/SRAM/SPI/UART/timer are models. */
#include "host098-prefix.inc"
#include "memory.h"
#include "actual-cfg.h"
#include "actual-sgb.h"
#include "actual-cic.h"
#define get_snes_reset unused_header_reset098
#include "actual-snes.h"
#undef get_snes_reset
#include "features098.inc"
#include "rtc098-enum.inc"
static cfg_t CFG;
static mcu_status_t STM;
static snes_status_t STS;
static sgb_romprops_t sgb_romprops;
static unsigned scenario098,baseline098,blocked098,menu_bytes098,sideeffects098;
static unsigned firstboot,rtc_state,rtc_set098,pair098,reliable098,menu_enter098;
static unsigned writes_at_release098;
static unsigned file_block_off,file_block_max,file_status;
static uint8_t file_buf[512];
static char current_filename[512];
static uint32_t sram_crc_valid,sram_crc_init,sram_crc_romsize,saveram_crc_old,saveram_crc,saveram_offset;
int sd_offload_tgt;
static jmp_buf blocked_env098;
void card_autoboot098(void);
#define FILE_OK 0
#define FILE_ERR 1
#define MENU_FILENAME "/sd2snes/m3nu.bin"
#define FPGA_DSP ((const uint8_t*)"unused-dsp")
#define print_fresult(...) ((void)0) /* formatting only; UART is not tested */
#include "fileops098.inc"

static unsigned forbidden098(void){assert(!"unreachable legacy path");return 0;}
#define file_read(...) forbidden098()
#define snescmd_readbyte(...) forbidden098()
#define snescmd_writebyte(...) forbidden098()
#define sgb_id(...) forbidden098()
#define sgb_update_file(...) forbidden098()
#define smc_id(...) forbidden098()
#define gbc_load_rom(...) forbidden098()
#define snes_set_snes_cmd(...) forbidden098()
#define snes_get_mcu_cmd(...) forbidden098()
#define set_mcu_addr(...) forbidden098()
#define load_sram_offload(...) forbidden098()
#define set_bsx_regs(...) forbidden098()
#define srtctime2bcdtime(...) forbidden098()
#define load_dspx(...) forbidden098()
#define snes_menu_errmsg(...) forbidden098()
#define migrate_and_load_srm(...) forbidden098()
#define calc_sram_crc(...) forbidden098()
#define msu1_check(...) forbidden098()
#define cli_entrycheck(...) forbidden098()
#define assert_reset(...) forbidden098()
#define init(...) forbidden098()
#define deassert_reset(...) forbidden098()
#define cfg_load(...) forbidden098()
#define cfg_save(...) forbidden098()
#define cfg_validity_check_listed_games(...) forbidden098()
#define cfg_dump_listed_games_for_snes(...) forbidden098()
#define led_pwm(...) forbidden098()
/* Only the inactive SGB contract is modeled; real SGB bodies not executed. */
static unsigned sgb_update_model098(void){assert(!sgb_romprops.has_sgb&&!sgb_romprops.has_egbc);return 1;}
#define sgb_update_romprops(...) sgb_update_model098()
#define sgb_load_sram(...) ((void)sgb_update_model098())
#define sgb_gtc_load(...) ((void)sgb_update_model098())
#define gbc_save_disarm(...) ((void)0)
#define gbc_dump_disarm(...) ((void)0)

static bool model_io098(void){
 if(nes_return_failed())return false;
 assert(!irq&&nes_diag_active());sideeffects098++;return true;
}
#define MODEL_VOID(n,args) static void n args {(void)model_io098();}
MODEL_VOID(set_rom_mask,(uint32_t v))
MODEL_VOID(set_mapper,(uint8_t v))
MODEL_VOID(set_saveram_mask,(uint32_t v))
MODEL_VOID(set_saveram_base,(uint8_t v))
MODEL_VOID(fpga_set_features,(uint16_t v))
MODEL_VOID(fpga_set_213f,(uint8_t v))
MODEL_VOID(fpga_set_chipfeat,(uint16_t v))
MODEL_VOID(fpga_set_dac_boost,(uint8_t v))
MODEL_VOID(fpga_dspx_reset,(uint8_t v))
MODEL_VOID(fpga_reset_srtc_state,(void))
MODEL_VOID(fpga_write_cheat,(uint8_t a,uint16_t v))
MODEL_VOID(dac_pause,(void))
MODEL_VOID(dac_reset,(uint8_t v))
MODEL_VOID(set_fpga_time,(uint64_t v))
MODEL_VOID(led_set_brightness,(uint8_t v))
MODEL_VOID(rdyled,(unsigned v))
MODEL_VOID(readled,(unsigned v))
MODEL_VOID(writeled,(unsigned v))
static void uart_putc(unsigned c){(void)c;}
static void uart_putcrlf(void){}
static uint8_t rtc_isvalid(void){return scenario098==1?1:RTC_OK;}
static void set_bcdtime(uint64_t t){assert(t==0x20120701000000LL);rtc_set098++;}
static uint64_t get_bcdtime(void){return 0x20261008123456LL;}
static void invalidate_rtc(void){rtc_set098++;}
void cic_init(int allow){assert(!allow);}
static void cic_pair_model098(void){pair098++;}
#define cic_pair(...) cic_pair_model098()
static enum cicstates get_cic_state_model098(void){
 if((scenario098==4&&!menu_enter098)||(scenario098==8&&release097))return CIC_FAIL;
 if(scenario098==2)return CIC_PAIR;
 if(scenario098==3)return CIC_SCIC;
 return CIC_OK;
}
#define get_cic_state() get_cic_state_model098()
void snes_reset(int v){
 if(!v){assert(!irq&&!nes_return_failed());release097++;writes_at_release098=card_writes096();if(scenario098==14)card_phase_fault096(6,3,1);}
 reset_held=v;
}
void nes_diag_blocked(void){assert(!irq);blocked098++;longjmp(blocked_env098,1);}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){
 if(!model_io098())return 0;
 assert(a+n<=sizeof(menu_ram097));
 if(scenario098==7&&a==SRAM_MENU_CFG_ADDR){nes_return_fail(NES_DIAG_SPI);return 0;}
 if(scenario098==9&&a==SRAM_MCU_STATUS_ADDR){nes_return_fail(NES_DIAG_SPI);return 0;}
 if(a>=SRAM_MENU_ADDR&&a<SRAM_MENU_ADDR+65536){assert(reset_held);menu_bytes098+=n;menu_writes097++;}
 memcpy(menu_ram097+a,p,n);return n;
}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){
 if(!model_io098())return 0;
 assert(a+n<=sizeof(menu_ram097));memcpy(p,menu_ram097+a,n);menu_reads097++;
 if(scenario098==6&&a==SRAM_MENU_ADDR+32768)((uint8_t*)p)[0]^=1;
 return n;
}
void sram_writebyte(uint8_t v,uint32_t a){(void)sram_writeblock(&v,a,1);}
void sram_writelong(uint32_t v,uint32_t a){(void)sram_writeblock(&v,a,4);}
uint8_t sram_readbyte(uint32_t a){uint8_t v=0;sram_readblock(&v,a,1);return v;}
void sram_memset(uint32_t a,uint32_t n,uint8_t v){if(model_io098()){assert(a+n<=sizeof(menu_ram097));memset(menu_ram097+a,v,n);}}
uint32_t sram_readlong(uint32_t a){
 reliable098++;if(!model_io098())return 0;
 assert(a==SRAM_SCRATCHPAD);
 if((scenario098==10&&reliable098==128)||(scenario098==11&&reliable098==384))return 0;
 uint32_t v=0;memcpy(&v,menu_ram097+a,4);return v;
}
#include "reliable098.inc"
#include "helpers098.inc"
#include "load098.inc"
#include "main098.inc"

int main(int argc,char **argv){
 signal(SIGABRT,failed096);assert(argc==9);setvbuf(stdout,0,_IONBF,0);
 scenario098=(unsigned)strtoul(argv[1],0,10);baseline098=(unsigned)strtoul(argv[2],0,10);
 FILE*f=fopen(argv[3],"rb");assert(f);original_length=fread(rom,1,sizeof(rom),f);fclose(f);
 diag_packed097=read_file097(argv[4],&diag_size097);diag_raw097=read_file097(argv[5],&diag_raw_size097);
 base_packed097=read_file097(argv[6],&base_size097);base_raw097=read_file097(argv[7],&base_raw_size097);menu097=read_file097(argv[8],&menu_size097);
 initialize(NONE,1);mock_a.IDR=32;
 if(scenario098==5)menu097[100]^=1;
 card_profile096(scenario098==12||original_length==98320?3:0);card_setup096(rom,original_length);
 if(scenario098==13)card_autoboot098();
 native_ns096=ns=0;poll096=0;measured096=1;
 assert(nes_menu_diagnostic_run((const uint8_t*)(original_length==98320?"NES VERIFY 094 96.nh1":"NES VERIFY 094 80.nh1")));
 assert(configs==2&&!irq&&reset_held&&finishes==1&&check_acks==original_length-16&&!memcmp(loaded,rom+16,original_length-16));
 /* main begins only after base restoration; firstboot=false is intentional. */
 STS.is_u16=STS.u16_cfg=(scenario098==3);CFG.brightness_limit=15;
 memset(menu_ram097,0xa5,sizeof(menu_ram097));card_stage097(6);
 bool ok=false;
 if(scenario098>=20){
  nes_return_io_begin();unsigned cmds=card_commands096();
  if(scenario098<26){
   uint32_t addr=scenario098==20?0:scenario098==21?SRAM_MENU_ADDR+1:scenario098==22?0xffffffffu:SRAM_MENU_ADDR;
   const char *path=scenario098==24?"/sd2snes/not-menu.bin":MENU_FILENAME;
   unsigned fl=scenario098==23?LOADROM_WITH_RESET:scenario098==25?LOADROM_WITH_COMBO:0;
   assert(load_rom((uint8_t*)path,addr,fl)==0&&card_commands096()==cmds);
  }else assert(!nes_return_copy_menu(MENU_FILENAME,scenario098==26?0:scenario098==27?SRAM_MENU_ADDR+1:SRAM_MENU_ADDR,scenario098==28?1:0));
  assert(nes_return_failed()&&!irq&&reset_held&&!menu_bytes098&&!release097);
  printf("PASS098 scenario=%u rejected invalid destination/path/flags/offset before SRAM IO\n",scenario098);return 0;
 }
 if(!setjmp(blocked_env098))ok=actual_main098();
 if(baseline098){assert(!ok&&blocked098&&nes_return_failed()&&menu_bytes098==0&&!release097&&!irq&&reset_held);puts("REPRO098 actual main 0xC00000 rejected by old zero-address guard");}
 else if(scenario098==0||scenario098==1||scenario098==2||scenario098==3||scenario098==12||scenario098==13){
  assert(ok&&!blocked098&&release097==1&&irq&&!reset_held&&!nes_menu_diagnostic_pending()&&!nes_diag_active());
  assert(menu_bytes098==65536&&!memcmp(menu097,menu_ram097+SRAM_MENU_ADDR,65536));
  for(unsigned i=0;i<65536;i++)assert(menu_ram097[i]==0xa5);
  assert(!memcmp(&CFG,menu_ram097+SRAM_MENU_CFG_ADDR,sizeof(CFG))&&!memcmp(&STM,menu_ram097+SRAM_MCU_STATUS_ADDR,sizeof(STM)));
  assert(STM.num_recent_games==0&&STM.num_favorite_games==0&&STM.rtc_valid==(scenario098==1?255:0));
  assert(rtc_set098==(scenario098==1?2:0)&&pair098==(scenario098==2?1:0));
  assert(STM.autoboot_enabled==(scenario098==13));
  assert(reliable098==512&&card_writes096()==5&&writes_at_release098==5);
 }else{
  assert(!ok&&blocked098&&!irq&&reset_held&&nes_menu_diagnostic_pending()&&nes_diag_active());
  assert(release097==(scenario098==8||scenario098==9||scenario098==11||scenario098==14?1:0));
  if(scenario098==4||scenario098==5)assert(menu_bytes098==0);
 }
 if(first_error096)assert(card_commands096()==first_commands096&&frames==first_frames096&&configs==first_configs096&&config_bytes096==first_bytes096&&card_edges096()==first_edges096);
 printf("PASS098 scenario=%u baseline=%u copied=%u release=%u blocked=%u error=%u commands=%u\n",scenario098,baseline098,menu_bytes098,release097,blocked098,nes_diag_status()->error,card_commands096());return 0;
}
