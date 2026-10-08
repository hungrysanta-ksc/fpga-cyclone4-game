# SPDX-License-Identifier: MIT
"""New CF86 upper MCU variant; frozen044/056 prefix and069 inputs unchanged."""
from pathlib import Path
import argparse,json,shutil
from nes_cf68_mcu import materialize as base
from nes_menu_diagnostic import replace
from nes_diag_recovery_checks import function
from nes_mcu_loader import FW,sha


def adapt(out):
    for n in ['nes_cf86_session094.c','nes_cf86_session094.h']:
        shutil.copy2(FW/n,out/n)
    p=out/'nes_h1_stm32.c'; s=p.read_text(); at=s.index('bool nes_menu_sd_probe(')
    prefix=s[:at]; body=s[at:]
    # Preserve all historical entry functions byte-for-byte, append a checked
    # private transaction variant for CF86 short identity frames.
    short=function(prefix,'slow_transaction').replace('slow_transaction(', 'cf86_short094(',1)
    short=replace(short,' if(!gpio_owned || n<1 || n>3)return false;',
                  ' if(!nes_cf86_check094()||!gpio_owned || n<1 || n>3)return false;')
    short=replace(short,'  for(unsigned bit=0;bit<8;bit++) {',
                  '  for(unsigned bit=0;bit<8;bit++) {\n   if(!nes_cf86_check094())goto cancel094;')
    short=replace(short,'   value=(uint8_t)', '   if(!nes_cf86_check094())goto cancel094;\n   value=(uint8_t)')
    short=replace(short,' return true;',' return nes_cf86_check094();\ncancel094:\n SET_BIT(FPGA_SSREG,FPGA_SSBIT);CLEAR_BIT(GPIOB,3);return false;')
    helper='''
#include "nes_cf86_session094.h"
static void cf86_end094(void){
 if(nes_cf86_check094()){slow_end();return;}
 if(gpio_owned){SET_BIT(FPGA_SSREG,FPGA_SSBIT);CLEAR_BIT(GPIOB,3);CLEAR_BIT(GPIOB,5);gpio_owned=false;}
 /* Keep hardware SPI disabled and PB4 input; never restore stale output/AF. */
}
'''+short+'\n'
    body=body.replace('slow_transaction(', 'cf86_short094(')
    body=replace(body,'if(rx[1]!=0x68)','if(rx[1]!=0x86)')
    body=replace(body,' nes_diag_sd_reset();nes_diag_begin();',
        ' if(!nes_cf86_enter094())return false;\n nes_diag_sd_reset();nes_diag_begin();')
    body=replace(body,' if(!slow_begin())', ' if(!nes_cf86_arm094()){r->result=NES_MCU_LOAD_CONFIG;goto cleanup;}\n if(!slow_begin())')
    body=replace(body,'cleanup:\n if(opened)', '''cleanup:
 if(nes_cf86_monitoring094())(void)nes_cf86_check094();
 if(nes_return_failed()||(changed_fpga&&(r->result!=NES_MCU_LOAD_OK||!report->verified)))nes_cf86_fail094();
 if(opened&&!nes_cf86_failed094()&&!nes_return_failed())''')
    body=replace(body,' if(gpio_owned && begin_sent && !r->stop_ok)',
                 ' if(!nes_cf86_failed094()&&gpio_owned && begin_sent && !r->stop_ok)')
    body=replace(body,' slow_end();', ''' if(changed_fpga&&begin_sent&&!r->stop_ok)nes_cf86_fail094();
 if(nes_cf86_failed094())report->verified=false;
 cf86_end094();
 if(!nes_cf86_finish094()){report->verified=false;nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}''')
    body=replace(body,'fpga_test()!=FPGA_TEST_TOKEN){nes_diag_progress',
                 'fpga_test()!=FPGA_TEST_TOKEN){nes_cf86_fail094();report->verified=false;nes_diag_progress')
    p.write_text(prefix+helper+body,encoding='utf-8',newline='\n')
    p=out/'nes_rom_spi.c';s=p.read_text();s=replace(s,'#include <stddef.h>','#include <stddef.h>\n#include "nes_cf86_session094.h"')
    s=replace(s,' io->clock(io->ctx,false);io->select', ' if(!nes_cf86_check094())return false;\n io->clock(io->ctx,false);io->select')
    s=replace(s,'  for(unsigned b=0;b<8;b++){','  for(unsigned b=0;b<8;b++){\n   if(!nes_cf86_check094())goto cancel094;')
    s=replace(s,'   value=(uint8_t)', '   if(!nes_cf86_check094())goto cancel094;\n   value=(uint8_t)')
    s=replace(s,' return true;\n}', ' return nes_cf86_check094();\ncancel094:\n io->select(io->ctx,false);io->clock(io->ctx,false);return false;\n}')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=out/'nes_rom_verify.c';s=p.read_text();s=replace(s,'#include <string.h>','#include <string.h>\n#include "nes_cf86_session094.h"')
    s=replace(s,'fail:\n if(opened', 'fail:\n if(nes_cf86_monitoring094())nes_cf86_fail094();\n if(opened')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=out/'nes_menu_diagnostic.c';s=p.read_text();s=s.replace('069','094').replace('CF68','CF86').replace('expected_hex=68','expected_hex=86').replace('fpga_nl8.bi3','fpga_n86.bi3')
    s=replace(s,'#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "nes_cf86_session094.h"')
    s=replace(s,' nes_return_reset();nes_diag_sd_reset();nes_diag_begin();',
        ' if(nes_cf86_failed094()||nes_return_failed())return false;\n nes_return_reset();nes_diag_sd_reset();nes_diag_begin();')
    p.write_text(s,encoding='utf-8',newline='\n')


def materialize(out):
    base(out);adapt(out)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    out=p.parse_args().out;out.mkdir(parents=True,exist_ok=False);materialize(out)
    (out/'sources094.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file()},indent=2)+'\n')
