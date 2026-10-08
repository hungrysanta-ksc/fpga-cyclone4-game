# SPDX-License-Identifier: MIT
"""Read-only audit of the frozen089 assembly/configuration/budget evidence."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/clock-config089-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():
  q=(e/n).resolve();assert q.is_relative_to(e) and sha(q)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 read=lambda n:json.loads((e/n).read_bytes())
 asm=read('asm01/result089.json');host=read('host04/result.json');arm=read('arm02/result.json')
 assert asm['rbf_bytes']==510856 and asm['rle_bytes']==59700
 assert sha(e/'asm01/output_files/board.rbf')==asm['rbf_sha256']==sha(e/'host04/golden.rbf')
 assert host['tests']==304 and host['config_checks']==31944
 assert [r['total_checks'] for r in host['combined']]==[729572,729572,921626]
 assert host['source_hashes']['nes_clock_config089.c']==arm['source_sha256']==sha(ROOT/'src/nes/firmware/nes_clock_config089.c')
 assert sha(e/'host04/nes_clock_config089.h')==arm['header_sha256']
 assert arm['object_bytes']==17876 and sha(e/'arm02/config.o')==arm['object_sha256']
 assert 'FROZEN089 shared_fault_checks=1000001 mini_return_bytes=74803 no_SD=1' in (e/'host04/host.log').read_text()
 for name in ['no-preflight-crc','no-stream-status','per-byte-budget','no-shared-guard']:
  r=read(name+'02/result.json');log=(e/(name+'02')/'host.log').read_text(errors='replace')
  assert r['mutation']==name and 'Assertion failed' in log and r['expected_failure'] in log
 for old in ['clock-observation087','clock-reader088']:
  prior=json.loads((ROOT/('analysis/'+old+'-verification.json')).read_bytes())
  for n,h in prior['public_sources'].items():assert sha(ROOT/n)==h,n
 assert not m['installable'] and not m['linked_firmware'] and not m['report_session_integrated']
 print('PASS089: same087 ASM,304 host checks/4 controls, shared budget729572/921626, ARM object only. SD/TXT session pending.')
if __name__=='__main__':main()
