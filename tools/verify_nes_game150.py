# SPDX-License-Identifier: MIT
"""Check frozen150 hashes without rerunning completed development work."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    m=json.loads((ROOT/'analysis/game150-verification.json').read_bytes());e=a.baseline/'nes-game150/evidence'
    assert sha(e/'manifest.json')==m['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    for n in ['video','client'] :assert json.loads((e/n/'result.json').read_bytes())['passed']
    assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
    assert 'PASS GAME150 ROM32768' in (e/'rom/simulation.log').read_text()
    arm=json.loads((e/'armcheck/result.json').read_bytes());assert arm['strong_nmi']
    assert sha(e/'arm/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
    package=json.loads((e/'release/result.json').read_bytes())
    assert sha(e/'release/NES150-SMB3-FIRST-RUN.zip')==package['zip_sha256']
    assert package['normal_trial_ready'] and not package['physical']
    print('PASS150 frozen game board/video/pad/ARM/package; physical game pending')
if __name__=='__main__':main()
