# SPDX-License-Identifier: MIT
"""Apply checkpoint changes once to an unchanged108 ARM or109 host source tree."""
from pathlib import Path
import shutil
from nes_spi_boot import ROOT
from nes_menu098 import once

def adapt(src):
    src=Path(src)
    def edit(n,old,new):
        p=src/n;text=p.read_text(encoding='utf-8')
        if n=='nes_h1_stm32.c' and not old.startswith('#include'):
            at=text.index('bool nes_menu_sd_probe(')
            text=text[:at]+once(text[at:],old,new)
        else:text=once(text,old,new)
        p.write_text(text,encoding='utf-8',newline='\n')
    for n in ['nes_checkpoint112.c','nes_checkpoint112.h']:
        shutil.copy2(ROOT/'src/nes/firmware'/n,src/n)
    edit('nes_menu_return.c','#include "nes_css108.h"','#include "nes_css108.h"\n#include "nes_checkpoint112.h"')
    edit('nes_menu_return.c','static struct nes_diag_wait io_wait;', '''static struct nes_diag_wait io_wait;
static bool checkpoint_window112,saved_io_active112;
static struct nes_diag_wait saved_io_wait112;
bool nes_return_checkpoint_enter112(void){
 if(checkpoint_window112||log_allowed||!nes_diag_active()||nes_return_failed())return false;
 saved_io_active112=io_active;saved_io_wait112=io_wait;checkpoint_window112=true;
 log_allowed=true;io_active=true;io_wait=nes_diag_wait_start(1000,10000u);return true;
}
void nes_return_checkpoint_leave112(void){
 if(!checkpoint_window112)return;
 log_allowed=false;io_active=saved_io_active112;io_wait=saved_io_wait112;checkpoint_window112=false;
 /* Original start time and remaining polls are restored, not restarted. */
}''')
    edit('nes_diag_runtime.c','#include "nes_css108.h"','#include "nes_css108.h"\n#include "nes_checkpoint112.h"')
    edit('nes_diag_runtime.c','report.total=total;nes_diag_observe(&report,active);',
         'report.total=total;nes_diag_observe(&report,active);\n if(active)nes_checkpoint_progress112(phase,completed,total);')
    edit('nes_h1_stm32.c','#include "nes_css108.h"','#include "nes_css108.h"\n#include "nes_checkpoint112.h"')
    edit('nes_h1_stm32.c','if(!nes_css_begin108()){nes_return_fail(NES_DIAG_SPI);return false;}',
         'if(!nes_css_begin108()){nes_return_fail(NES_DIAG_SPI);return false;}\n if(!nes_checkpoint_begin112())return false;')
    edit('nes_h1_stm32.c','if(!slow_begin()){r->result=NES_MCU_LOAD_OWNERSHIP;goto cleanup;}\n {',
         'if(!slow_begin()){r->result=NES_MCU_LOAD_OWNERSHIP;goto cleanup;}\n if(!nes_checkpoint112("CONFIG_READY",0,0)){r->result=NES_MCU_LOAD_SPI;goto cleanup;}\n {')
    edit('nes_h1_stm32.c','begin_sent=true; /* Completion may be unknown on a failed response. */',
         'if(!nes_checkpoint112("BEGIN_LOAD",0,total)){r->result=NES_MCU_LOAD_SPI;goto cleanup;}\n begin_sent=true; /* Completion may be unknown on a failed response. */')
    edit('nes_h1_stm32.c','/* No START: this entry only verifies and restores the base/menu path. */',
         'if(!nes_checkpoint112("STOP_START",total,total))r->result=NES_MCU_LOAD_SPI;\n /* No START: this entry only verifies and restores the base/menu path. */')
    edit('nes_h1_stm32.c','if(nes_diag_sd_failed()||nes_return_failed()){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}\n if(changed_fpga)',
         'if(nes_diag_sd_failed()||nes_return_failed()){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}\n if(!nes_checkpoint112("STOP_DONE",0,0))return false;\n if(changed_fpga)')
    edit('nes_h1_stm32.c','r->base_restored=true;\n }\n if(!nes_menu_diagnostic_pending())',
         'r->base_restored=true;\n  if(!nes_checkpoint112("BASE_DONE",0,0))return false;\n }\n if(!nes_menu_diagnostic_pending())')
    edit('nes_menu_return.c','if(nes_return_failed())return 0;\n FRESULT r=f_open',
         'if(nes_return_failed())return 0;\n if(!nes_checkpoint112("MENU_COPY_START",0,NES_MENU076_SIZE))return 0;\n FRESULT r=f_open')
    edit('nes_menu_diagnostic.c','#include "nes_cf86_session094.h"','#include "nes_cf86_session094.h"\n#include "nes_checkpoint112.h"')
    edit('nes_menu_diagnostic.c','prepared=true;return true;',
         'if(!nes_checkpoint112("MENU_PREPARED",65536,65536))return false;\n prepared=true;return true;')
