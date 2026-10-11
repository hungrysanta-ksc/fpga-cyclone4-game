# SPDX-License-Identifier: MIT
"""Reuse163 host/status tests only after exact source/identifier normalization."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','asm','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game163/evidence'
 meta=json.loads((ROOT/'analysis/game163-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 ap=json.loads((a.arm/'preparation164.json').read_bytes())
 changed={'src/VERSION','src/nes_menu_diagnostic.c','src/nes_checkpoint112.c'}
 assert set(ap['changed'])==changed;checked={}
 for n,h in ap['copied'].items():
  assert sha(e/'arm'/n)==pins['arm/'+n]==h
  assert sha(a.arm/n)==ap['changed'].get(n,h)
  if n in changed:assert (a.arm/n).read_text().replace('164','163')==(e/'arm'/n).read_text(),n
  checked[n]=sha(a.arm/n)
 status=json.loads((e/'status/result.json').read_bytes());host=json.loads((e/'host/result.json').read_bytes())
 for n in ['status/result.json','host/result.json']:assert sha(e/n)==pins[n]
 assert status['passed'] and host['passed']
 assert sha(a.asm/'nes_screen_status151.sv')==status['rtl_sha256']
 assert sha(a.arm/'src/nes_run136.inc')==host['source_sha256']
 assert sha(e/'arm/src/nes_menu_diagnostic.c')==host['format_source_sha256']
 old=json.loads((e/'client/result.json').read_bytes())
 assert sha(ROOT/'tools/nes_spc163.py')==old['sources']['tools/nes_spc163.py']
 result=dict(passed=True,method='Exact host sources except163->164 identifiers; unchanged status RTL/SPC generator',arm_source_checks=len(checked),normalized_files=sorted(changed),source_sha256=checked,status_cases_reused=status['cases'],host_recovery_cases_reused=host['recovery_cases'],host_formatter_masks_reused=host['formatter_masks'],spc_generator_sha256=sha(ROOT/'tools/nes_spc163.py'),scope='Reuses163 test results, not newly executed host/RTL/failure-injection cases. Actual164 ARM image and positive SNES/SPC/video tested separately.')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS164 reuse',len(checked),'ARM sources; status54/host13 and SPC unchanged')
if __name__=='__main__':main()
