# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence103','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence103.resolve();o=a.out.resolve();assert not o.exists()
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/observer103-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm01/'):continue
  n=key.removeprefix('arm01/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key;d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 f=o/'src/stm32f4xx/sdnative.c';s=f.read_text(encoding='utf-8')
 s=once(s,'    printf("ch ");','''    /* SysTick calls here. The foreground diagnostic owns the non-reentrant
     * formatter and UART; keep card-state updates without ISR output. */
    if(!nes_diag_active())printf("ch ");''')
 f.write_text(s,encoding='utf-8',newline='\n')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-IRQ104"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h};assert set(changed)=={'src/stm32f4xx/sdnative.c','src/VERSION'}
 shutil.copy2(__file__,o/'executed-prepare104.py')
 (o/'preparation104.json').write_text(json.dumps(dict(copied=copied,changed=changed,baseline_manifest_sha256=sha(e/'manifest.json'),physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS104 prepared diagnostic ISR printf suppression; card-state updates retained')
if __name__=='__main__':main()
