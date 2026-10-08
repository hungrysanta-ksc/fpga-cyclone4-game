# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence102','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence102.resolve();o=a.out.resolve();assert not o.exists()
 m=json.loads((ROOT/'analysis/quiesce102-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for key,h in pins.items():
  if not key.startswith('arm01/'):continue
  n=key.removeprefix('arm01/');parts=Path(n).parts
  if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files'] for x in parts):continue
  if Path(n).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(n).name=='.ARG_VERSION':continue
  assert sha(e/key)==h,key;d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,d);copied[n]=h
 f=o/'src/nes_diag_platform.c';s=f.read_text()
 s=once(s,'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"\nstatic void nes_diag_spi_quiesce102(void) __attribute__((noinline));')
 s=once(s,'void nes_diag_observe(const struct nes_diag_report *r,bool active) {','''void nes_diag_observe(const struct nes_diag_report *r,bool active) {
 /* Only the shared terminal latch authorizes irreversible isolation. A report
  * error alone can be recoverable. Do this before LED, tick, division or UART.
  * Do not change report/ownership or recurse into the runtime from here. */
 if(active&&nes_return_failed()) {
  NVIC_DisableIRQ(OTG_FS_IRQn);snes_reset(1);
  nes_diag_spi_quiesce102();
  return;
 }''')
 f.write_text(s,encoding='utf-8',newline='\n')
 f=o/'src/stm32f4xx/uart.c';s=f.read_text();s=once(s,'#include "nes_diag_runtime.h"','#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"')
 for name,args in [('uart_putc','char c'),('uart_flush','void')]:
  s=once(s,f'void {name}({args}) {{',f'''void {name}({args}) {{
  /* Best-effort diagnostics must not wait or access UART after shared fault. */
  if(nes_diag_active()&&nes_return_failed()){{nes_diag_uart_dropped++;return;}}''')
 f.write_text(s,encoding='utf-8',newline='\n')
 (o/'src/VERSION').write_text('RELEASE_VERSION = "CF86-OBS103"\n',encoding='utf-8')
 changed={n:sha(o/n) for n,h in copied.items() if sha(o/n)!=h}
 assert set(changed)=={'src/nes_diag_platform.c','src/stm32f4xx/uart.c','src/VERSION'},changed
 shutil.copy2(__file__,o/'executed-prepare103.py')
 (o/'preparation103.json').write_text(json.dumps(dict(baseline_manifest_sha256=sha(e/'manifest.json'),copied=copied,changed=changed,physical=False,installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS103 prepared early shared-fault isolation and UART suppression')
if __name__=='__main__':main()
