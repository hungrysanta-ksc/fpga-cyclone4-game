# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_lower100 import adapt

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence099',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence099.resolve();o=a.out.resolve();assert not o.exists()
 meta=json.loads((ROOT/'analysis/rtc099-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm01/'):continue
  n=key.removeprefix('arm01/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,dst);copied[n]=h
 adapt(o/'src');(o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-IO100"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/stm32f4xx/spi.c','src/fpga_spi.h','src/VERSION'},changed
 for n in ['prepare_nes_lower100.py','nes_lower100.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 (o/'preparation100.json').write_text(json.dumps(dict(baseline_manifest_sha256=sha(e/'manifest.json'),copied=copied,changed=changed,physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS100 prepared immutable099; SPI/header/VERSION only')
if __name__=='__main__':main()
