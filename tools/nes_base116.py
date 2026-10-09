# SPDX-License-Identifier: MIT
"""Instrument the exact113 source; no changes to shared CSS/NMI or legacy programmer."""
from pathlib import Path
from nes_menu098 import once

def adapt(src):
 src=Path(src)
 def edit(n,old,new):
  p=src/n;p.write_text(once(p.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 edit('nes_menu_diagnostic.c','static bool entry_only113;', 'static bool entry_only113,base_only116;\nbool nes_menu_base_only116(void){return base_only116;}')
 edit('nes_menu_diagnostic.c','if(!strcmp(name,"NES ENTRY 113.nh1"))return 113;', 'if(!strcmp(name,"NES ENTRY 113.nh1"))return 113;\n if(!strcmp(name,"NES BASE 116.nh1"))return 116;')
 edit('nes_menu_diagnostic.c','entry_only113=selected==113;geometry=entry_only113?80:selected;', 'entry_only113=selected==113;base_only116=selected==116;geometry=(entry_only113||base_only116)?80:selected;')
 edit('nes_h1_stm32.c','extern bool nes_menu_entry_only113(void);', '''extern bool nes_menu_entry_only113(void);
extern bool nes_menu_base_only116(void);
uint32_t nes_base_spi_sr116(void){return SPI1->SR;}
uint32_t nes_base_spi_cr116(void){return SPI1->CR1;}''')
 edit('nes_h1_stm32.c','if(!nes_checkpoint112("OPEN_INPUT",0,0))return false;', '''if(nes_menu_base_only116())goto configure116;
 if(!nes_checkpoint112("OPEN_INPUT",0,0))return false;''')
 edit('nes_h1_stm32.c','/* Independent checked programmer; errors return to protected recovery. */', 'configure116:\n /* Independent checked programmer; errors return to protected recovery. */')
 edit('nes_h1_stm32.c','if(!nes_checkpoint112("BEGIN_LOAD",0,total))', '''if(nes_menu_base_only116()) {
  if(!nes_checkpoint112("EMPTY_STOP_NEXT",0,0)){r->result=NES_MCU_LOAD_SPI;goto cleanup;}
  r->stop_ok=sd_command(&io,NES_ROM_STOP,0,0,&status);
  if(!r->stop_ok)r->result=NES_MCU_LOAD_SPI;
  goto cleanup;
 }
 if(!nes_checkpoint112("BEGIN_LOAD",0,total))''')
 edit('nes_h1_stm32.c','r->result!=NES_MCU_LOAD_OK||!report->verified', 'r->result!=NES_MCU_LOAD_OK||(!report->verified&&!nes_menu_base_only116())')
 edit('nes_h1_stm32.c', '''if(!nes_diag_fpga_pgm((const uint8_t *)FPGA_BASE)||!configured((const char *)FPGA_BASE) || (SPI1->SR&SPI_SR_BSY) ||
     !(SPI1->SR&SPI_SR_TXE) || fpga_test()!=FPGA_TEST_TOKEN){nes_cf86_fail094();report->verified=false;nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}''', '''bool base_ok=nes_diag_fpga_pgm((const uint8_t *)FPGA_BASE);
  if(!nes_return_failed()&&!nes_cf86_failed094())
   base_ok=nes_checkpoint112(base_ok?"BASE_PGM_OK":"BASE_PGM_REJECT",nes_diag_status()->error,0)&&base_ok;
  if(base_ok)base_ok=configured((const char *)FPGA_BASE);
  if(base_ok)base_ok=nes_checkpoint112("BASE_SPI_STATE_NEXT",0,0);
  if(base_ok)base_ok=!(SPI1->SR&SPI_SR_BSY)&&(SPI1->SR&SPI_SR_TXE);
  if(base_ok)base_ok=nes_checkpoint112("BASE_TOKEN_NEXT",0,0);
  if(base_ok) {
   uint8_t token=fpga_test();
   if(!nes_return_failed())base_ok=nes_checkpoint112("BASE_TOKEN_RESULT",token,FPGA_TEST_TOKEN);
   else base_ok=false;
   base_ok=base_ok&&token==FPGA_TEST_TOKEN;
  }
  if(!base_ok){nes_cf86_fail094();report->verified=false;nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}''')
 # Only the late base restoration is instrumented; CF86 configuration and
 # all non-diagnostic FPGA programming keep their existing behavior.
 n='fpga.c' if (src/'fpga.c').exists() else 'config.inc'
 edit(n,'bool nes_diag_fpga_pgm(const uint8_t *filename) {', '''extern bool nes_checkpoint112(const char *,uint32_t,uint32_t);
bool nes_diag_fpga_pgm(const uint8_t *filename) {''')
 edit(n,'uint32_t produced=0,remaining=0;int data=0;\n FRESULT res=f_open', '''uint32_t produced=0,remaining=0;int data=0;
 bool trace116=nes_diag_status()->phase==NES_DIAG_RECOVER;
 if(trace116&&!nes_checkpoint112("BASE_FILE_OPEN_NEXT",0,0))return false;
 FRESULT res=f_open''')
 edit(n,'fpga_init();fpga_config=0;gbc_spi_pacing=0;', '''if(trace116&&!nes_checkpoint112("BASE_FILE_OPENED",f_size(&in.file),0))return false;
 fpga_init();fpga_config=0;gbc_spi_pacing=0;''')
 edit(n,'FPGA_DIN_MASK();masked=true;', '''if(trace116&&!nes_checkpoint112("BASE_PINS_READY",0,0))return false;
 FPGA_DIN_MASK();masked=true;''')
 edit(n,'FPGA_DIN_UNMASK();masked=false;\n if(ok){', '''FPGA_DIN_UNMASK();masked=false;
 if(trace116&&!nes_return_failed()&&!nes_checkpoint112("BASE_STREAM_END",produced,ok?1u:0u))return false;
 if(nes_return_failed())return false;
 if(ok){''')
 edit(n,'ok=nes_diag_pin_wait(2,true,NES_DIAG_FPGA_DONE);', '''ok=nes_diag_pin_wait(2,true,NES_DIAG_FPGA_DONE);
  if(trace116&&!nes_return_failed()&&!nes_checkpoint112(ok?"BASE_DONE_HIGH":"BASE_DONE_TIMEOUT",produced,0))return false;''')
 # A checkpoint failure is terminal: do not close or issue any further IO.
 edit(n,'res=f_close(&in.file);', 'if(nes_return_failed())return false;\n res=f_close(&in.file);')
 edit('nes_checkpoint112.c','extern int nes_entry_transfer113;', 'extern int nes_entry_transfer113;\nextern uint32_t nes_base_spi_sr116(void),nes_base_spi_cr116(void);')
 edit('nes_checkpoint112.c','NES113 seq=', 'NES116 seq=')
 edit('nes_checkpoint112.c','entry_transfer=%d next_or_progress=1\\n', 'entry_transfer=%d spi_sr=%08lx spi_cr1=%08lx next_or_progress=1\\n')
 edit('nes_checkpoint112.c','*10u),nes_entry_transfer113);','*10u),nes_entry_transfer113,(unsigned long)nes_base_spi_sr116(),(unsigned long)nes_base_spi_cr116());')
 edit('nes_checkpoint112.c','/sd2snes/nes-progress-113.txt','/sd2snes/nes-progress-116.txt')
