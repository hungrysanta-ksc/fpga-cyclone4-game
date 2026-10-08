# SPDX-License-Identifier: MIT
"""Audit frozen C reader, actual GPIO replay, causal controls and ARM object."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/clock-reader088-verification.json').read_text());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_text())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():
  q=(e/n).resolve();assert q.is_relative_to(e) and sha(q)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 read=lambda n:json.loads((e/n).read_text())
 normal=read('host05/result.json');absent=read('absent06/result.json');arm=read('arm01/result.json')
 assert normal['tests']==absent['tests']==1966
 for host in [normal,absent]:
  assert host['sources']['nes_clock_reader088.c']==arm['source_sha256']==sha(ROOT/'src/nes/firmware/nes_clock_reader088.c')
  assert host['sources']['nes_clock_reader088.h']==arm['header_sha256']
 assert sha(e/'host04/wave.txt')==sha(e/'host05/wave.txt')==normal['wave_sha256']
 prior=json.loads((ROOT/'analysis/clock-observation087-verification.json').read_text())
 for n,h in prior['public_sources'].items():assert sha(ROOT/n)==h,n
 for folder,host in [('wave01',normal),('absent-wave01',absent)]:
  r=read(folder+'/result.json');assert r['checked_bits']==73456 and r['rows']==295453 and r['end_ns']==3005436000
  assert r['wave_sha256']==host['wave_sha256']==sha(e/folder/'wave.txt')
  assert r['production_sources']==m['cf87_generated_sources']
  log=(e/folder/'simulation.log').read_text(errors='replace');assert '** Fatal:' not in log and 'PASS C_READER088' in log
 for n in ['no-pair-check','no-deadline','no-owner-check']:
  r=read(n+'01/result.json');log=(e/(n+'01')/'host.log').read_text(errors='replace')
  assert r['mutation']==n and r['expected_failure'] in log and 'Assertion failed' in log
 r=read('wrong-divider01/result.json');assert r['expected_failure']=='C_MISO_MISMATCH'
 assert 'C_MISO_MISMATCH' in (e/'wrong-divider01/simulation.log').read_text(errors='replace')
 assert arm['arm_object_only'] and not arm['linked_firmware']
 assert not m['installable'] and not m['hardware_execution'] and not m['report_session_integrated']
 print('PASS reader088: host1966/3 C controls,2 actual GPIO replays146912bits/RTL control1, same ARM object source. TXT session/firmware/hardware pending.')
if __name__=='__main__':main()
