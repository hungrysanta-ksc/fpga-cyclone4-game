# SPDX-License-Identifier: MIT
"""Add SD response checks to frozen076 source, compile-only."""
from pathlib import Path
import argparse,json,hashlib,shutil
from nes_sd_response077 import adapt
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence076',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();e=a.evidence076
 assert sha(e/'manifest.json')=='648144bf654b167b7316f77673eceb5b0f097ec566e5f382d030d6ef897aec0c'
 assert not a.out.exists();pins=json.loads((e/'arm/build-inputs.json').read_bytes())
 for n,h in pins.items():assert sha(e/'arm/source'/n)==h,n
 shutil.copytree(e/'arm/source',a.out)
 f=a.out/'src/stm32f4xx/sdnative.c';f.write_text(adapt(f.read_text()),encoding='utf-8',newline='\n')
 (a.out/'src/VERSION').write_bytes(b'RELEASE_VERSION = "NES-SD077-CF68"\r\n')
 (a.out/'preparation077.json').write_text(json.dumps(dict(baseline076=sha(e/'manifest.json'),baseline_inputs=pins,inputs={p.relative_to(a.out).as_posix():sha(p) for p in a.out.rglob('*') if p.is_file()},installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS077 prepared from frozen076; only native SD + VERSION changed; compile-only')
if __name__=='__main__':main()
