# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_run136_mcu import adapt

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence116','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence116.resolve();o=a.out.resolve();assert not o.exists()
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/base116-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm01/'):continue
  n=key.removeprefix('arm01/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 adapt(o/'src')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "NES-RUN136"\n',encoding='utf8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/VERSION','src/nes_menu_diagnostic.c','src/nes_h1_stm32.c','src/nes_checkpoint112.c'}
 (o/'preparation136.json').write_text(json.dumps(dict(copied=copied,changed=changed),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-prepare136.py');print('PASS136 prepared from immutable116')
if __name__=='__main__':main()
