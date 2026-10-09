# SPDX-License-Identifier: MIT
"""Apply entry-only probe and bounded legacy SD handoff to exact112 sources."""
from pathlib import Path
from nes_spi_boot import ROOT
from nes_menu098 import once

def adapt(src):
 src=Path(src)
 def edit(n,old,new):
  f=src/n;f.write_text(once(f.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 body=(ROOT/'src/nes/firmware/nes_sd_entry113.inc').read_text(encoding='utf-8')
 native=src/'stm32f4xx/sdnative.c'
 target='stm32f4xx/sdnative.c' if native.exists() else 'native.inc'
 edit(target,'static DRESULT nes_diag_sd_read(',body+'\nstatic DRESULT nes_diag_sd_read(')
 edit('nes_menu_diagnostic.c','static unsigned geometry;', 'static unsigned geometry;\nstatic bool entry_only113;\nbool nes_menu_entry_only113(void){return entry_only113;}')
 edit('nes_menu_diagnostic.c','const char *names[2]=', 'if(!strcmp(name,"NES ENTRY 113.nh1"))return 113;\n const char *names[2]=')
 edit('nes_menu_diagnostic.c','geometry=selected;pending=true;', 'entry_only113=selected==113;geometry=entry_only113?80:selected;pending=true;')
 edit('nes_h1_stm32.c','bool nes_menu_sd_probe(', '''extern bool nes_menu_entry_only113(void);
extern bool nes_diag_sd_handoff113(void);
bool nes_entry_owner113(void){
 return get_snes_reset()&&!NVIC_GetEnableIRQ(OTG_FS_IRQn);
}
bool nes_menu_sd_probe(''')
 edit('nes_h1_stm32.c', '''if(!nes_cf86_enter094())return false;
 nes_diag_sd_reset();nes_diag_begin();
 if(!nes_css_begin108()){nes_return_fail(NES_DIAG_SPI);return false;}
 if(!nes_checkpoint_begin112())return false;''', '''/* Still running the original base FPGA. Drain a completed legacy read
  * before the CF86 owner check; never clear an uncertain transaction. */
 if(!nes_diag_sd_handoff113()){nes_return_fail(NES_DIAG_SD_STATE);return false;}
 if(!nes_checkpoint_begin112())return false;
 if(!nes_cf86_enter094())return false;
 if(!nes_checkpoint112("CSS_CHECK_NEXT",0,0))return false;
 if(!nes_css_begin108()){nes_return_fail(NES_DIAG_SPI);return false;}
 if(!nes_checkpoint112("CSS_READY",0,0))return false;
 if(nes_menu_entry_only113()) {
  if(!nes_cf86_finish094())return false;
  return nes_checkpoint112("ENTRY_ONLY_DONE",0,0);
 }
 if(!nes_checkpoint112("OPEN_INPUT",0,0))return false;''')
 edit('nes_checkpoint112.c','static bool enabled;', 'extern int nes_entry_transfer113;\nstatic bool enabled;')
 edit('nes_checkpoint112.c','NES112 seq=%lu stage=%s bytes=%lu total=%lu elapsed_ms=%lu next_or_progress=1\\n', 'NES113 seq=%lu stage=%s bytes=%lu total=%lu elapsed_ms=%lu entry_transfer=%d next_or_progress=1\\n')
 edit('nes_checkpoint112.c','(unsigned long)((uint32_t)(nes_diag_ticks()-started)*10u));', '(unsigned long)((uint32_t)(nes_diag_ticks()-started)*10u),nes_entry_transfer113);')
 edit('nes_checkpoint112.c','/sd2snes/nes-progress-112.txt','/sd2snes/nes-progress-113.txt')
 edit('nes_checkpoint112.c','return nes_checkpoint112("OPEN_INPUT",0,0);','return nes_checkpoint112("ENTRY_SD_READY",0,0);')

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('src',type=Path);a=p.parse_args();adapt(a.src)
