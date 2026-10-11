# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game157-verification.json').read_bytes());e=a.baseline/'nes-game157/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','host','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
 assert sha(e/'release/NES157-SMB3-PPU-HISTORY.zip')==m['package']['zip_sha256']
 assert not m['physical_test'] and not m['ppu_fix'] and m['fit']['m9k']==56
 print('PASS157 frozen evidence/public pins/package:',len(files),'files')
if __name__=='__main__':main()
