# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile
from nes_spi_boot import ROOT,sha
from nes_pair109 import expected,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 meta=json.loads((ROOT/'analysis/base116-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==meta['archived_files']
 for n,h in pins.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 tests=json.loads((e/'host03/result.json').read_bytes());assert len(tests['cases'])==8
 for c in tests['cases']:assert sha(e/f"host03/case-{c['case']}.log")==c['log_sha256']
 for n in [70,71]:
  data=(e/f'host03/case-{n}-logical.txt').read_bytes();assert len(data)%512==0 and b'MENU_PREPARED' in data
 short=(e/'host03/case-71-logical.txt').read_bytes();assert b'EMPTY_STOP_NEXT' in short and b'BEGIN_LOAD' not in short
 for n in ['nes_menu_diagnostic.c','nes_h1_stm32.c','nes_checkpoint112.c']:
  assert sha(e/'arm01/src'/n)==sha(e/'host03'/n)
 actual=(e/'arm01/src/fpga.c').read_text(encoding='utf-8');actual=actual[actual.index('struct nes_diag_input '):].strip()
 assert actual==(e/'host03/config.inc').read_text(encoding='utf-8').strip()
 arm=json.loads((e/'arm-check02/result.json').read_bytes());assert arm==meta['arm']
 assert sha(e/'arm01/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 obs=json.loads((e/'hardware115/interpretation.json').read_bytes())
 assert sha(e/'hardware115/received-nes-progress-113.txt')==obs['input_sha256']=='fec7b3ad9a78c0d955c2ea6cf7942a3140b1f54fb234f4c55618e2d542810891'
 assert obs['last_stage']=='BASE_START' and obs['user_report']['restore_this_run'].startswith('skipped')
 zpath=e/'release01/NES116-BASE-RECOVERY-and-RESTORE044.zip';assert sha(zpath)==meta['release']['zip_sha256']
 with zipfile.ZipFile(zpath) as z:
  assert len(z.namelist())==11 and not any(n.endswith('.nes') for n in z.namelist())
  m=json.loads(z.read('manifest.json'))
  for n,v in m['files'].items():
   assert len(z.read(n))==v['bytes'] and digest(z.read(n))==v['sha256']
   if v['role']:assert v['sha256']==(arm['firmware_sha256'] if v['role']=='arm116.stm' else expected()[v['role']]['sha256'])
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-base116-instructions.ko.md').read_bytes()
  assert z.read('01-BASE-SD-ROOT/NES BASE 116.nh1')==b''
  d=json.loads(z.read('decision116.json'));assert d['human_limit_seconds']==60 and d['attempts']==1
  assert not any(d[k] for k in ['full_nes_installable','start_enabled','electrical_signoff','common_cause_8us_proven'])
 print('PASS116 evidence/physical115 observation/host-ARM source identity/short recovery/faults/exact package; physical116 pending')
if __name__=='__main__':main()
