# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_spi_boot import ROOT,sha
from nes_pair105 import verify

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
 m=json.loads((ROOT/'analysis/pair105-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h==sha(e/'public-sources'/n),n
 assert sha(e/'review02/executed-prepare105.py')==m['public_sources']['tools/prepare_nes_pair105.py']
 assert sha(e/'tests01/executed-test105.py')==m['public_sources']['tools/test_nes_pair105.py']
 r=verify(e/'review02',m['pair_manifest_sha256']);assert r['pair_identity_pass'] and not r['policy']['installable']
 t=json.loads((e/'tests01/result.json').read_bytes());assert t['normal']==1 and t['rejected']==23 and len(t['cases'])==24
 assert not t['cases'][0]['rejected'] and all(x['rejected'] for x in t['cases'][1:])
 assert not m['new_arm'] and not m['new_asm'] and not m['physical'] and not m['installable']
 print('PASS105 frozen11 roles/24preflight cases; pair identity only, installation not approved')
if __name__=='__main__':main()
