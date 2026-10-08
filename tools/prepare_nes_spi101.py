# SPDX-License-Identifier: MIT
"""Materialize immutable100 and fix diagnostic TXE-before-BSY ordering only."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence100',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 e=a.evidence100.resolve();o=a.out.resolve();assert not o.exists()
 meta=json.loads((ROOT/'analysis/lower100-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm02/'):continue
  n=key.removeprefix('arm02/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 f=o/'src/stm32f4xx/spi.c';s=f.read_text()
 s=once(s,' if(!nes_return_spi_wait(SPI_SR_BSY_Pos,false))return 0;',''' /* A DR write can precede BSY assertion. Drain the transmit buffer first. */
 if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return 0;
 if(!nes_return_spi_wait(SPI_SR_BSY_Pos,false))return 0;''')
 s=once(s,' if(!nes_return_spi_wait(SPI_SR_TXE_Pos,true))return 0;\n SPI1->DR=data;',
 ''' /* TXE was established before BSY, and this owned diagnostic path has
  * not written DR since. Do not spend the shared budget checking it twice. */
 SPI1->DR=data;''')
 s=once(s,'  if(nes_diag_active()){(void)nes_return_spi_wait(SPI_SR_BSY_Pos,false);return;}','''  if(nes_diag_active()){
    /* RM0368 20.3.8: TXE must precede BSY after the last DR write.
     * A fault abandons this frame; this is not peripheral/pad shutdown. */
    if(nes_return_spi_wait(SPI_SR_TXE_Pos,true))
      (void)nes_return_spi_wait(SPI_SR_BSY_Pos,false);
    return;
  }''')
 f.write_text(s,encoding='utf-8',newline='\n')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-SPI101"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/stm32f4xx/spi.c','src/VERSION'},changed
 shutil.copy2(__file__,o/'executed-prepare101.py')
 (o/'preparation101.json').write_text(json.dumps(dict(baseline_manifest_sha256=sha(e/'manifest.json'),copied=copied,changed=changed,physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS101 prepared: diagnostic sync/exchange ordering; legacy unchanged')
if __name__=='__main__':main()
