# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence104','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence104.resolve();o=a.out.resolve();assert not o.exists()
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/timer104-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm01/'):continue
  n=key.removeprefix('arm01/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 def edit(n,old,new):
  f=o/'src'/n;f.write_text(once(f.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 for n in ['nes_css108.c','nes_css108.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,o/'src'/n)
 edit('Makefile','nes_cf86_session094.c nes_rom_spi.c','nes_cf86_session094.c nes_css108.c nes_rom_spi.c')
 edit('nes_menu_return.c','#include "nes_menu076.h"','#include "nes_menu076.h"\n#include "nes_css108.h"')
 edit('nes_menu_return.c','return fault||nes_diag_sd_failed();','return nes_css_fault108()||fault||nes_diag_sd_failed();')
 edit('nes_diag_runtime.c','#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_css108.h"')
 edit('nes_diag_runtime.c','void nes_diag_leave(void){active=false;','void nes_diag_leave(void){if(!nes_css_end108())nes_diag_blocked();active=false;')
 edit('nes_h1_stm32.c','#include "nes_cf86_session094.h"','#include "nes_cf86_session094.h"\n#include "nes_css108.h"')
 edit('nes_h1_stm32.c','nes_diag_sd_reset();nes_diag_begin();','''nes_diag_sd_reset();nes_diag_begin();
 if(!nes_css_begin108()){nes_return_fail(NES_DIAG_SPI);return false;}''')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-CSS108"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/Makefile','src/nes_menu_return.c','src/nes_diag_runtime.c','src/nes_h1_stm32.c','src/VERSION'}
 shutil.copy2(__file__,o/'executed-prepare108.py')
 (o/'preparation108.json').write_text(json.dumps(dict(copied=copied,changed=changed,added={n:sha(o/'src'/n) for n in ['nes_css108.c','nes_css108.h']},physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS108 prepared scoped CSS/NMI and lifecycle/shared-fault hooks')
if __name__=='__main__':main()
