# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,zipfile
from nes_spi_boot import ROOT,sha
from nes_pair109 import expected,digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 meta=json.loads((ROOT/'analysis/entry113-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==meta['archived_files']
 for n,h in pins.items():assert sha(e/n)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 for d,count in [('baseline01',1),('host02',10)]:
  r=json.loads((e/d/'result.json').read_bytes());assert len(r['cases'])==count
  for c in r['cases']:assert sha(e/d/f"case-{c['case']}.log")==c['log_sha256']
 assert (e/'baseline01/case-61-records.txt').stat().st_size==0
 for n in [60,61,70]:
  data=(e/f'host02/case-{n}-logical.txt').read_bytes();assert len(data)%512==0 and b'MENU_PREPARED' in data
 for n in ['nes_menu_diagnostic.c','nes_h1_stm32.c','nes_checkpoint112.c']:
  assert sha(e/'arm01/src'/n)==sha(e/'host02'/n)
 body=(ROOT/'src/nes/firmware/nes_sd_entry113.inc').read_text(encoding='utf-8')
 assert body in (e/'arm01/src/stm32f4xx/sdnative.c').read_text(encoding='utf-8')
 assert body in (e/'host02/native.inc').read_text(encoding='utf-8')
 arm=json.loads((e/'arm-check01/result.json').read_bytes());assert arm==meta['arm']
 assert sha(e/'arm01/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
 zpath=e/'release01/NES113-ENTRY-ONLY-and-RESTORE044.zip';assert sha(zpath)==meta['release']['zip_sha256']
 with zipfile.ZipFile(zpath) as z:
  assert len(z.namelist())==10
  m=json.loads(z.read('manifest.json'))
  for n,v in m['files'].items():
   assert len(z.read(n))==v['bytes'] and digest(z.read(n))==v['sha256']
   if v['role']:assert v['sha256']==(arm['firmware_sha256'] if v['role']=='arm113.stm' else expected()[v['role']]['sha256'])
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-entry113-instructions.ko.md').read_bytes()
  assert z.read('01-ENTRY-SD-ROOT/NES ENTRY 113.nh1')==b''
  d=json.loads(z.read('decision113.json'));assert d['human_limit_seconds']==60 and d['attempts']==1
  assert not any(d[k] for k in ['full_nes_installable','start_enabled','electrical_signoff','common_cause_8us_proven'])
 print('PASS113 frozen evidence/112 failure reproduction/entry log readback/host-ARM sources/exact restore package; physical pending')
if __name__=='__main__':main()
