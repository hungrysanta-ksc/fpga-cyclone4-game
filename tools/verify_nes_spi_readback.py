# SPDX-License-Identifier: MIT
"""059 raw-evidence audit; private057 baseline/live/fit/ARM files required."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_spi_boot import ROOT,sha,put
from nes_spi_readback import materialize
from nes_spi_live import compare_case

def audit(evidence,baseline):
 records={}
 for mode in ['unit','wave','live','fit']:
  folder=evidence/mode;r=json.loads((folder/'result.json').read_text())
  assert r['candidate']=='NES-SPI-READBACK-059' and r['mode']==mode and r['passed']
  for n,h in r['sources'].items():assert sha(folder/n)==h,n
  assert sha(folder/'nes_spi_readback_checks.py')==r['driver_sha256']
  if mode in ['unit','wave']:
   log=(folder/'vsim.log').read_text(errors='replace')
   assert r['marker'] in log and 'Errors: 0, Warnings: 0' in log
   assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  if mode=='fit':
   log=(folder/'output_files/live.fit.rpt').read_text(errors='replace')
   assert re.search(r'Total LABs:.*?;\s*959 / 963',log)
   assert re.search(r'M9Ks\s*;\s*26 / 56',log)
   assert '14,180 / 15,408' in r['fit_summary'] and 'Total registers : 5203' in r['fit_summary']
  records[mode]=r
 assert 'checks=149 negative_cases=18' in records['unit']['marker']
 assert 'checked_bits=5656 pin_bytes=81920 checked_bytes=32 source_failure_STOP=1' in records['wave']['marker']
 for mode,name in [('unit','spi_readback_control_tb.sv'),('wave','spi_readback_pin_tb.sv')]:
  assert sha(ROOT/'tests/nes-functional'/name)==records[mode]['sources'][name]
 with tempfile.TemporaryDirectory(prefix='nes059-audit-') as tmp:
  out=Path(tmp);materialize(out)
  for n in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','nes_spi_boot.sv','nes_rom_spi.sv']:
   assert sha(out/n)==records['fit']['sources'][n]==records['live']['sources'][n]==records['wave']['sources'][n]
  assert sha(out/'nes_rom_spi.sv')==records['unit']['sources']['nes_rom_spi.sv']
 cases=[]
 for case in ['banks32','fine_x']:
  c=compare_case(evidence/'live',baseline,case);c['tick_offsets_vs057']=c.pop('tick_offsets_vs053');cases.append(c)
  log=(evidence/'live'/case/'simulation.log').read_text(errors='replace')
  assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
  oldlog=(baseline/case/'simulation.log').read_text(errors='replace')
  warnings=re.search(r'Errors: 0, Warnings: (\d+)',log)
  oldwarnings=re.search(r'Errors: 0, Warnings: (\d+)',oldlog)
  assert warnings and oldwarnings and warnings[1]==oldwarnings[1]
  c['simulation_warnings']=int(warnings[1]);c['baseline_simulation_warnings']=int(oldwarnings[1])
  total=98304 if case=='banks32' else 81920
  assert f'CHECK PROGRESS bytes={total}' in log
 host=json.loads((evidence/'host/result.json').read_text())
 assert host['host_model_pass'] and not host['actual_stm32_execution']
 for n,h in host['sources'].items():assert sha(evidence/'host'/n)==h
 assert sha(evidence/'host/waveform.txt')==host['waveform_sha256']==records['wave']['waveform_sha256']
 assert host['marker'] in (evidence/'host/host.log').read_text()
 assert sha(evidence/'host/executed-driver.py')==host['driver_sha256']
 mutation=json.loads((evidence/'host-mutation/result.json').read_text())
 assert mutation['negative_control_verified'] and not mutation['incorrect_design_passed'] and mutation['exit_code']!=0
 for n,h in mutation['sources'].items():assert sha(evidence/'host-mutation'/n)==h
 assert sha(evidence/'host-mutation/host.log')==mutation['log_sha256']
 assert sha(evidence/'host-mutation/executed-driver.py')==mutation['driver_sha256']
 assert '!nes_rom_verify(&io,total,source,0,&r)' in (evidence/'host-mutation/host.log').read_text()
 arm=json.loads((evidence/'arm/result.json').read_text());assert arm['full_link'] and arm['functions_uncalled']
 for n,h in arm['files'].items():assert sha(evidence/'arm'/n)==h
 symbols=(evidence/'arm/symbols.txt').read_text()
 for name,size in arm['functions_bytes'].items():
  symbol=re.search(r'^[0-9a-fA-F]+ ([0-9a-fA-F]+) T '+name+r'$',symbols,re.M)
  assert symbol and int(symbol[1],16)==size,name
 for n in ['nes_rom_verify.c','nes_rom_verify.h']:
  assert sha(evidence/'host'/n)==sha(ROOT/'src/nes/firmware'/n)==sha(evidence/'arm'/n)
 for name in ['source-manifest.json','cores/nes/publication-sources.json']:
  for e in json.loads((ROOT/name).read_text())['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
 return dict(candidate='NES-SPI-READBACK-059',date_kst='2026-10-07',passed=True,hardware_image=False,actual_stm32_execution=False,
  sd_menu_binding=False,cases=cases,unit=records['unit']['marker'],wave=records['wave']['marker'],host=host,negative_control=mutation,
  joint_fit=dict(LE=14180,LAB=959,total_LAB=963,remaining_LAB=4,registers=5203,M9K=26,virtual_pins=288,physical_unlocated_pins=22,PLL=0),
  runs=records,arm=arm,protected_files=dict(GBC=152,original_NES=334))

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=audit(a.evidence,a.baseline);put(a.out,json.dumps(r,indent=2)+'\n');print('PASS059 raw evidence and protected sources')

if __name__=='__main__':main()
