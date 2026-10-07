# SPDX-License-Identifier: MIT
"""Audit private074 evidence; not a public-clone hardware reproduction."""
from pathlib import Path
import argparse,hashlib,json,re,zipfile,zlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def audit(e):
 meta=load(ROOT/'analysis/sd-fault074-verification.json');assert sha(e/'manifest.json')==meta['manifest_sha256']
 m=load(e/'manifest.json');assert len(m['files'])==meta['archived_files']
 for n,h in m['files'].items():
  p=(e/n).resolve();assert p.is_relative_to(e.resolve()) and sha(p)==h,n
 for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
 for n,h in meta.get('archived_public_sources',meta['public_sources']).items():assert sha(e/'public-source'/n)==h,n
 pins=load(ROOT/'analysis/sd-write-recovery-inputs.json')
 for n,h in pins.items():assert sha(e/'arm/source/src'/n)==h,n
 for n,h in load(e/'arm/build-inputs.json').items():assert sha(e/'arm/source'/n)==h,n
 assert [load(e/'host/result.json')[n] for n in ['collector','writer','platform','led','report']]==[52,23,6,162,29]
 assert load(e/'integration/result.json')['checks']==40
 assert load(e/'mutation/mutation-result.json')['rejected']
 assert 'nr==e+1&&nw==stage' in (e/'mutation/mutation.log').read_text()
 for n in ['nes_sd_inventory.c','nes_sd_inventory_log.c','nes_sd_inventory_platform.c','nes_diag_platform.c']:
  assert sha(e/'host'/n)==sha(e/'arm/source/src'/n),n
 assert sha(e/'integration/nes_sd_inventory_log073.c')==sha(e/'arm/source/src/nes_sd_inventory_log.c')
 fw=(e/'arm/firmware.stm').read_bytes();assert len(fw)==133332 and sha(e/'arm/firmware.stm')=='031725700f3e9c58abc1001f9d53cdbe89a1587e5e552a77951434d136953271'
 assert fw[:4]==b'STM3' and int.from_bytes(fw[8:12],'little')==len(fw)-512 and int.from_bytes(fw[12:16],'little')==zlib.crc32(fw[512:]) and b'SDINFO074-BASE069' in fw
 for name in ['nes_diag_observe','nes_diag_led_tick']:
  text=(e/'arm'/(name+'.txt')).read_text(errors='replace')
  assert not re.search(r'<(?:printf|uart|snes_bootprint|f_write|cmd_fast|spi)',text)
 text=(e/'arm/sdinv_write_report.txt').read_text(errors='replace');assert text.count('<nes_return_log_allow>')==2 and '<write_report>' in text
 extra=e.parent/'audit-addendum/write_report.txt';assert sha(extra)==meta['arm_write_report_sha256']
 text=extra.read_text(errors='replace');assert text.count('<sdinv_fault_stage>')==7
 text=(e/'arm/main.txt').read_text(errors='replace');assert re.findall(r'\bbl(?:\.w)?\s+\w+\s+<([^>]+)>',text)[-1]=='sdinv_run'
 text=(e/'arm/nes_diag_blocked.txt').read_text(errors='replace');assert '<nes_diag_led_tick>' in text and '<snes_reset>' in text
 text=(e/'arm/SysTick_Handler.txt').read_text(errors='replace');assert '<led_error>' in text
 text=(e/'arm/led_error.txt').read_text(errors='replace');assert '<nes_diag_led_tick>' in text
 kit=load(e/'kit/manifest.json');assert kit['payload_paths']==['sd2snes/firmware.stm'] and not kit['root_cause_fixed']
 with zipfile.ZipFile(e/'kit/FXPAK-SDINFO074-SD.zip') as z:assert z.read('sd2snes/firmware.stm')==fw and z.testzip() is None
 observed=load(e/'observed.json');assert observed['file_bytes']==0 and observed['screen']=='blank' and not observed['raw_file_received']
 print('PASS074 frozen='+str(len(m['files']))+' LED162/causal1/FatFS40/52+23+6+29/ARM; hardware cause unresolved')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);audit(p.parse_args().evidence)
