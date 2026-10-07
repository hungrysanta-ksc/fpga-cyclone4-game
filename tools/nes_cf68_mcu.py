# SPDX-License-Identifier: MIT
"""069 MCU overlay for frozen068 CF68 diagnostic; compile-only."""
from pathlib import Path
import argparse,json,shutil
from nes_menu_return import materialize as base,prepare as prepare065
from nes_menu_diagnostic import replace
from nes_mcu_loader import sha

def adapt(out):
 p=out/'nes_h1_stm32.c';s=p.read_text()
 s=replace(s,'if(rx[1]!=0x61)','if(rx[1]!=0x68)')
 s=replace(s,' if(!slow_begin()){r->result=NES_MCU_LOAD_OWNERSHIP;goto cleanup;}\n {',
   ' if(!nes_return_spi_ready()){r->result=NES_MCU_LOAD_CONFIG;goto cleanup;}\n if(!slow_begin()){r->result=NES_MCU_LOAD_OWNERSHIP;goto cleanup;}\n {')
 s=replace(s,'if(nes_diag_sd_failed()){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}',
   'if(nes_diag_sd_failed()||nes_return_failed()){nes_diag_progress(NES_DIAG_BLOCKED,0,0);return false;}')
 p.write_text(s,encoding='utf-8',newline='\n')
 p=out/'nes_menu_diagnostic.c';s=p.read_text()
 for old,new in [('NES VERIFY 065','NES VERIFY 069'),('NES-MENU-DIAGNOSTIC-065','NES-CF68-MCU-069'),('NES065','NES069'),('nes-verify-last-065','nes-verify-last-069'),('board_expected_hex=61','board_expected_hex=68'),('fpga_nlv.bi3','fpga_nl8.bi3')]:s=s.replace(old,new)
 p.write_text(s,encoding='utf-8',newline='\n')

def materialize(out):base(out);adapt(out)
def prepare(baseline,out):
 prepare065(baseline,out);adapt(out/'src')
 old=json.loads((out/'menu-return-preparation.json').read_text())
 (out/'cf68-preparation.json').write_text(json.dumps(dict(candidate='NES-CF68-MCU-069',expected_cf=0x68,installable=False,baseline_preparation_sha256=sha(out/'menu-return-preparation.json'),files={n:sha(out/'src'/n) for n in old['files']}),indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.baseline,a.out)
