# SPDX-License-Identifier: MIT
"""Verify frozen private076 archive and public sources; not a public-only build."""
from pathlib import Path
import argparse,json,hashlib,zlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence;m=json.loads((ROOT/'analysis/menu076-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['files']
 assert set(files)=={p.relative_to(e).as_posix() for p in e.rglob('*') if p.is_file() and p!=e/'manifest.json'}
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 result=json.loads((e/'tests/check076.json').read_bytes());assert result['host_checks']==853 and result['causal_mutations']==2 and result['unchanged_pinned069']==272 and not result['installable']
 fw=e/'arm/firmware.stm';raw=fw.read_bytes();assert len(raw)==180108 and sha(fw)==result['firmware_sha256'];assert raw[:4]==b'STM3' and int.from_bytes(raw[8:12],'little')==len(raw)-512 and int.from_bytes(raw[12:16],'little')==zlib.crc32(raw[512:]) and b'NES-MENU076-CF68' in raw
 for n,h in json.loads((e/'tests/host-03/result.json').read_bytes())['inputs'].items():assert sha(e/'arm/source/src'/n)==h,n
 for name in ['class-crc','copy-crc']:
  r=json.loads((e/('tests/mutation-'+name)/'result.json').read_bytes());assert r['exit'] and r['mutation']==name
 for n,h in json.loads((e/'arm/build-inputs.json').read_bytes()).items():assert sha(e/'arm/source'/n)==h,n
 print('PASS076 frozen='+str(len(files))+' host853/causal2/ARM called menu/272 unchanged069; installable=0')
if __name__=='__main__':main()
