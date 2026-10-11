# SPDX-License-Identifier: MIT
"""Check frozen153 and the exact reused152 FPGA; no repeated build/simulation."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    m=json.loads((ROOT/'analysis/game153-verification.json').read_bytes());e=a.baseline/'nes-game153/evidence'
    assert sha(e/'manifest.json')==m['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    for n in ['host','context']:assert json.loads((e/n/'result.json').read_bytes())['passed']
    assert json.loads((e/'armcheck/result.json').read_bytes())['strong_nmi']
    assert sha(e/'release/NES153-SMB3-FAULT-RECOVERY.zip')==m['package']['zip_sha256']
    old=a.baseline/'nes-game152/evidence'
    assert sha(old/'manifest.json')==m['reused152']['manifest_sha256']
    assert sha(old/'asm/fpga_n152.bi3')==m['package']['fpga_sha256']
    assert m['package']['fpga_identical152'] and not m['ppu_deadline_fixed'] and not m['physical_test']
    print('PASS153 integrity; tagged error recovery model passed; actual hardware/PPU root cause pending')

if __name__=='__main__':main()
