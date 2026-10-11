# SPDX-License-Identifier: MIT
"""Verify frozen151 without rebuilding or replaying completed simulations."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    m=json.loads((ROOT/'analysis/game151-verification.json').read_bytes());e=a.baseline/'nes-game151/evidence'
    assert sha(e/'manifest.json')==m['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    for n in ['test','client']:assert json.loads((e/n/'result.json').read_bytes())['passed']
    assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
    assert json.loads((e/'armcheck/result.json').read_bytes())['strong_nmi']
    assert sha(e/'release/NES151-SMB3-WRITE-END.zip')==m['package']['zip_sha256']
    assert m['sd_package'] and not m['physical_test']
    print('PASS151 frozen write-completion/game-hold/ARM/package integrity; hardware pending')
if __name__=='__main__':main()
