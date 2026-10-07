# SPDX-License-Identifier: MIT
"""Verify private077 archive; no hardware installation or public-only claim."""
from pathlib import Path
import argparse,hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence;m=json.loads((ROOT/'analysis/sd-response077-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['files']
 assert set(files)=={p.relative_to(e).as_posix() for p in e.rglob('*') if p.is_file() and p!=e/'manifest.json'}
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 checks=json.loads((e/'tests/check077.json').read_bytes());test=json.loads((e/'tests/run-03/result.json').read_bytes())
 assert checks['checks_each']==43 and checks['mutations']==2 and not checks['installable'] and not checks['physical']
 assert sha(e/'arm/source/src/stm32f4xx/sdnative.c')==test['candidate_sha256']
 for name in ['baseline','candidate']:assert test['results'][name]=={'checks':43,'exit':0}
 for name in ['no-end','short-tail']:assert test['results'][name]['exit']!=0
 data=(e/'arm/firmware.stm').read_bytes();assert len(data)==180128 and sha(e/'arm/firmware.stm')==checks['firmware_sha256'];assert data[:4]==b'STM3' and int.from_bytes(data[8:12],'little')==len(data)-512 and int.from_bytes(data[12:16],'little')==zlib.crc32(data[512:]) and b'NES-SD077-CF68' in data
 for n,h in json.loads((e/'arm/build-inputs.json').read_bytes()).items():assert sha(e/'arm/source'/n)==h,n
 print('PASS077 frozen='+str(len(files))+' baseline43/candidate43/causal2/ARM write calls; hardware=0 installable=0')
if __name__=='__main__':main()
