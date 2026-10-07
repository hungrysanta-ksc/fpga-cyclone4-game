# SPDX-License-Identifier: MIT
"""062 called manual menu candidate from hash-verified private060 ARM inputs."""
from pathlib import Path
import argparse,json,shutil
from nes_menu_diagnostic import materialize,main_source,replace
from nes_sd_readback import source as source060
from nes_mcu_loader import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 old=json.loads((a.baseline/'sd-readback-preparation.json').read_text())
 assert old['candidate']=='NES-SD-READBACK-060'
 for n,h in old['files'].items():assert sha(a.baseline/'src'/n)==h,n
 assert (a.baseline/'src/nes_h1_stm32.c').read_text()==source060()
 assert not a.out.exists()
 shutil.copytree(a.baseline,a.out,ignore=shutil.ignore_patterns('obj*','.dep*','*.elf','*.stm','*.map','*.lst'))
 materialize(a.out/'src')
 main=a.out/'src/main.c';main.write_text(main_source(main.read_text()),encoding='utf-8',newline='\n')
 mk=a.out/'src/Makefile';s=mk.read_text()
 s=replace(s,'SRC += nes_h1_session.c nes_h1_stm32.c','SRC += nes_h1_session.c nes_h1_stm32.c nes_menu_diagnostic.c')
 s=replace(s,' -Wl,--undefined=nes_sd_readback_probe','')
 mk.write_text(s,encoding='utf-8',newline='\n')
 assert main.read_text().count('nes_menu_diagnostic_run(file_lfn)')==3
 assert 'file_lfn[0] && !nes_h1_is_marker(file_lfn)' in main.read_text()
 assert '"NH1"' in (a.out/'src/filetypes.c').read_text()
 names=['nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h',
  'nes_sd_readback.h','nes_menu_probe.h','nes_menu_diagnostic.c','nes_menu_diagnostic.h','main.c','filetypes.c','Makefile']
 (a.out/'menu-diagnostic-preparation.json').write_text(json.dumps(dict(candidate='NES-MENU-DIAGNOSTIC-062',manual_entry_hooks=3,
  autoboot='NACK',start_enabled=False,installable=False,baseline_preparation_sha256=sha(a.baseline/'sd-readback-preparation.json'),
  files={n:sha(a.out/'src'/n) for n in names}),indent=2)+'\n')
 print('Prepared062 three actual manual hooks; compile-only, not for installation')

if __name__=='__main__':main()
