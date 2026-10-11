# SPDX-License-Identifier: MIT
"""Verify selected152 without repeating completed build/simulation jobs."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game152-verification.json').read_bytes());e=a.baseline/'nes-game152/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','client','old-client']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
 assert json.loads((e/'armcheck/result.json').read_bytes())['strong_nmi']
 assert sha(e/'release/NES152-SMB3-INPUT-CONTEXT.zip')==m['package']['zip_sha256']
 assert m['sd_package'] and not m['physical_test'] and not m['ppu_error_fixed']
 print('PASS152 integrity; input/context hardware pending; PPU fault remains open')
if __name__=='__main__':main()
