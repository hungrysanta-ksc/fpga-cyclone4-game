# SPDX-License-Identifier: MIT
"""New private094 copy + exact two address guards; keep all old evidence immutable."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import adapt

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence094',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence094.resolve();o=a.out.resolve();assert not o.exists()
 meta=json.loads((ROOT/'analysis/session094-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 # Only manifested files, excluding build outputs/caches. Retain build support.
 for key,h in pins.items():
  if not key.startswith('arm04/'):continue
  n=key.removeprefix('arm04/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,dst);copied[n]=h
 adapt(o/'src');(o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-MENU098"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/memory.c','src/nes_menu_return.c','src/VERSION'},changed
 shutil.copy2(__file__,o/'executed-prepare098.py');shutil.copy2(ROOT/'tools/nes_menu098.py',o/'executed-adapter098.py')
 (o/'preparation098.json').write_text(json.dumps(dict(baseline_manifest_sha256=sha(e/'manifest.json'),copied=copied,changed=changed,physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS098 prepared exact094; two C guards + VERSION changed')
if __name__=='__main__':main()
