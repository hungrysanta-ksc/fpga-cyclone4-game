# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_checkpoint112 import adapt
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence108','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence108.resolve();o=a.out.resolve();assert not o.exists()
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/css108-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm02/'):continue
  n=key.removeprefix('arm02/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 adapt(o/'src')
 f=o/'src/Makefile';f.write_text(once(f.read_text(encoding='utf-8'),'nes_css108.c nes_rom_spi.c','nes_css108.c nes_checkpoint112.c nes_rom_spi.c'),encoding='utf-8',newline='\n')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-LOG112"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/Makefile','src/VERSION','src/nes_diag_runtime.c','src/nes_menu_return.c','src/nes_menu_diagnostic.c','src/nes_h1_stm32.c'}
 (o/'preparation112.json').write_text(json.dumps(dict(copied=copied,changed=changed,added={n:sha(o/'src'/n) for n in ['nes_checkpoint112.c','nes_checkpoint112.h']}),indent=2)+'\n',encoding='utf-8')
 shutil.copy2(__file__,o/'executed-prepare112.py');print('PASS112 prepared from immutable108 ARM source')
if __name__=='__main__':main()
