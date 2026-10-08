# SPDX-License-Identifier: MIT
"""Verify private094 frozen evidence and current public inputs, without builds."""
from pathlib import Path
import argparse,json
from nes_mcu_loader import sha,ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/session094-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 entries=json.loads((e/'manifest.json').read_bytes())['files'];assert len(entries)==m['archived_files']
 for n,h in entries.items():
  f=(e/n).resolve();assert f.is_relative_to(e) and sha(f)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 normal=json.loads((e/'host04/result.json').read_bytes());assert len(normal['cases'])==63
 assert all(x['exit']==0 and 'PASS094' in x['last_line'] for x in normal['cases'])
 for name in ['ready','latch','verify-fail','candidate']:
  r=json.loads((e/('causal03-'+name)/'result.json').read_bytes())
  assert r['mutation']==name and r['expected_failures'] and r['cases'][0]['exit']!=0
 arm=json.loads((e/'nes-session094-arm04-check02.json').read_bytes())
 assert arm['firmware_sha256']==m['firmware_sha256']
 src=e/'arm04/src';host=e/'host04'
 for n,h in arm['host_arm_identical'].items():assert sha(src/n)==sha(host/n)==h,n
 fw=src/'obj-nes-094/firmware.stm';assert sha(fw)==m['firmware_sha256'] and fw.stat().st_size==180928
 assert arm['actual_native077_retained'] and arm['legacy_prefix_identical']
 assert not m['installable'] and not m['physical'] and not m['full_cf86_rtl_replay']
 print('PASS094: frozen63 cases/4 causal controls, nine same ARM inputs, linked180928 bytes; no physical/RTL replay approval')
if __name__=='__main__':main()
