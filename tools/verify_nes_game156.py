# SPDX-License-Identifier: MIT
"""Verify frozen156 evidence, source pins, changed boundaries and private ZIP."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game156-verification.json').read_bytes());e=a.baseline/'nes-game156/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for part in ['test','host']:assert json.loads((e/part/'result.json').read_bytes())['passed']
 assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
 assert sha(e/'release/NES156-SMB3-SOUND-PAD.zip')==m['package']['zip_sha256']
 assert not m['physical_test'] and not m['gameplay_passed']
 print('PASS156 frozen evidence/public sources/package:',len(files),'files')
if __name__=='__main__':main()
