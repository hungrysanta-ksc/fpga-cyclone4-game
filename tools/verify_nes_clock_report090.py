# SPDX-License-Identifier: MIT
"""Read-only audit of frozen090 full session and linked firmware evidence."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence.resolve()
 m=json.loads((ROOT/'analysis/clock-report090-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():
  q=(e/n).resolve();assert q.is_relative_to(e) and sha(q)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 read=lambda n:json.loads((e/n).read_bytes())
 host=read('host02/result.json');arm=read('arm01/arm-check090.json');txt=read('text01/result.json')
 assert host['checks']==94 and len(host['reports'])==16 and txt['corruption_rejections']==4
 assert 'DENSE090 no_progress prewrite=955390 writer=60 native=110' in (e/'host02/host.log').read_text()
 for n in arm['host_same']:assert sha(e/'host02'/n)==sha(e/'arm01/source/src'/n),n
 assert sha(e/'arm01/source/src/obj-report079/firmware.stm')==m['firmware_sha256']==arm['firmware_sha256']
 assert arm['firmware_bytes']==196248 and arm['menu_runtime_prefix_exact']
 for n in ['skip-reader','clear-reader-fault','skip-readback','skip-rehold']:
  r=read(n+'01/result.json');log=(e/(n+'01')/'host.log').read_text(errors='replace');assert r['mutation']==n and 'Assertion failed' in log and r['expected_failure'] in log
 for prior in ['clock-observation087','clock-reader088','clock-config089']:
  for n,h in json.loads((ROOT/('analysis/'+prior+'-verification.json')).read_bytes())['public_sources'].items():assert sha(ROOT/n)==h,n
 assert m['linked_firmware'] and m['report_session_integrated'] and not m['installable'] and not m['hardware_execution']
 print('PASS090:94 full-session checks/4 causal controls/16 TXT parses/4 corruptions; linked196248-byte ARM, physical unverified.')
if __name__=='__main__':main()
