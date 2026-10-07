# SPDX-License-Identifier: MIT
"""Audit060 private raw evidence; does not rerun simulations or physical tests."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_spi_boot import ROOT,sha,put
from nes_sd_readback import source
from nes_mcu_loader import source as source056
from nes_spi_readback import materialize

def audit(raw,previous):
 host=json.loads((raw/'host/result.json').read_text());assert host['host_model_pass'] and host['candidate']=='NES-SD-READBACK-060'
 assert (raw/'host/nes_h1_stm32.c').read_text()==source()
 assert source().startswith(source056()+'\n')
 for mode in ['host','mutation-crc','mutation-close']:
  folder=raw/mode;r=json.loads((folder/'result.json').read_text())
  for n,h in r['files'].items():assert sha(folder/n)==h,n
  assert sha(folder/'executed-driver.py')==r['driver_sha256']
  log=(folder/'host.log').read_text(errors='replace')
  if mode=='host':assert r['marker'] in log
  else:assert r['expected_failure_verified'] and not r['incorrect_design_passed'] and 'Assertion failed: r->result==expected' in log
 wave=json.loads((raw/'wave/result.json').read_text());assert wave['rtl_replay'] and not wave['actual_stm32_execution']
 assert sha(raw/'wave/executed-driver.py')==wave['driver_sha256']
 assert sha(raw/'host/result.json')==wave['host_result_sha256']
 for n,h in wave['sources'].items():assert sha(raw/'wave'/n)==h,n
 for c in wave['cases']:
  log=(raw/'wave'/c['mode']/'simulation.log').read_text(errors='replace')
  assert c['marker'] in log and 'Errors: 0, Warnings: 0' in log
  assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  name='load-waveform.txt' if c['mode']=='load' else 'waveform.txt'
  key='load_waveform_sha256' if c['mode']=='load' else 'waveform_sha256'
  assert sha(raw/'host'/name)==c['waveform_sha256']==host[key]==sha(raw/'wave'/c['mode']/'waveform.txt')
 assert 'checked=29024 pin_bytes=256 verified_bytes=0' in wave['cases'][0]['marker']
 assert 'checked=43288 pin_bytes=98304 verified_bytes=256' in wave['cases'][1]['marker']
 fit=json.loads((previous/'fit/result.json').read_text())
 with tempfile.TemporaryDirectory(prefix='nes060-audit-') as d:
  out=Path(d);materialize(out)
  for n in ['nes_rom_spi.sv','nes_spi_boot.sv','nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv']:
   assert sha(out/n)==wave['sources'][n]==fit['sources'][n]==sha(previous/'fit'/n),n
 arm=json.loads((raw/'arm/result.json').read_text());assert arm['full_link'] and not arm['menu_entry']
 for n,h in arm['files'].items():assert sha(raw/'arm'/n)==h,n
 assert (raw/'arm/nes_h1_stm32.c').read_text()==source()
 for n in ['nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h','nes_sd_readback.h']:
  assert sha(raw/'arm'/n)==sha(raw/'host'/n)==sha(ROOT/'src/nes/firmware'/n),n
 match=re.search(r'^\w+ (\w+) T nes_sd_readback_probe$',(raw/'arm/symbols.txt').read_text(),re.M)
 assert match and int(match[1],16)==1068
 for name in ['source-manifest.json','cores/nes/publication-sources.json']:
  for e in json.loads((ROOT/name).read_text())['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
 return dict(candidate='NES-SD-READBACK-060',date_kst='2026-10-07',passed=True,hardware_image=False,actual_stm32_execution=False,
  host=host,wave=wave,arm=arm,negative_controls=['missing final source CRC rejected','failed final close ignored: rejected'],
  previous_fit_reused=dict(candidate='NES-SPI-READBACK-059',LAB=959,total_LAB=963,remaining_LAB=4,M9K=26,new_fit=False,result_sha256=sha(previous/'fit/result.json')),
  full_core_rerun=False,last_full_core='NES-SPI-READBACK-059',protected_files=dict(GBC=152,original_NES=334))

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--previous059',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=audit(a.evidence,a.previous059);put(a.out,json.dumps(r,indent=2)+'\n');print('PASS060 source/wave/ARM/protected-source audit')

if __name__=='__main__':main()
