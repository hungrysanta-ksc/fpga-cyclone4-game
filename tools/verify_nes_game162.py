# SPDX-License-Identifier: MIT
"""Read-only verification of frozen162 sources, evidence and private package."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game162-verification.json').read_bytes());e=a.baseline/'nes-game162/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files']
 assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['audio','regression','host']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 for n in ['timing150-phase.json','audio162-timing.json']:assert json.loads((e/'asm'/n).read_bytes())['passed']
 for n,h in m['package']['reused161_sources'].items():assert sha(e/'asm'/n)==h,n
 assert not m['physical_audio'] and not m['continuous_video'] and m['fit']['m9k']==56
 assert sha(e/'release/NES162-SMB3-AUDIO.zip')==m['package']['zip_sha256']
 with zipfile.ZipFile(e/'release/NES162-SMB3-AUDIO.zip') as z:
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game162-instructions.ko.md').read_bytes()
  assert z.read('01-GAME162-SD-ROOT/sd2snes/firmware.stm')==(e/'arm/src/obj-nes-100/firmware.stm').read_bytes()
  assert z.read('01-GAME162-SD-ROOT/sd2snes/fpga_n162.bi3')==(e/'asm/fpga_n162.bi3').read_bytes()
 print('PASS162 frozen evidence/public pins/package:',len(files),'files; audio/APU/ROM boundaries; audio hardware pending')
if __name__=='__main__':main()
