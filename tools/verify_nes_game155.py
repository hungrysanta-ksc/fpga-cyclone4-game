# SPDX-License-Identifier: MIT
"""Verify frozen155 evidence, selected results and public source pins."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game155-verification.json').read_bytes());e=a.baseline/'nes-game155/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files']
 assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for part in ['collision','reuse','decoder']:assert json.loads((e/part/'result.json').read_bytes())['passed']
 assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
 assert sha(e/'release/NES155-SMB3-BG-PREFETCH.zip')==m['package']['zip_sha256']
 assert m['physical_test'] is False and m['gameplay_passed'] is False
 print('PASS155 frozen evidence/public sources/package:',len(files),'files')
if __name__=='__main__':main()
