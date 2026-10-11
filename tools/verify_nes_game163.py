# SPDX-License-Identifier: MIT
"""Verify frozen163 evidence, public sources, ROM-content update and package."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game163-verification.json').read_bytes());e=a.baseline/'nes-game163/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['client','status','host']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 fit=json.loads((e/'asm/result163.json').read_bytes());assert fit['passed'] and not fit['new_map_fit']
 assert sha(e/'asm/game-program.hex')==fit['program_sha256']==json.loads((e/'client/result.json').read_bytes())['program_sha256']
 for n,h in fit['unchanged_routing_and_sources'].items():assert sha(e/'asm'/n)==h,n
 assert sha(e/'asm'/fit['generated_mif'])==fit['mif_sha256']
 zpath=e/'release/NES163-SMB3-SPC-AUDIO.zip';assert sha(zpath)==m['package']['zip_sha256']
 with zipfile.ZipFile(zpath) as z:
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game163-instructions.ko.md').read_bytes()
  assert z.read('01-GAME163-SD-ROOT/sd2snes/firmware.stm')==(e/'arm/src/obj-nes-100/firmware.stm').read_bytes()
  assert z.read('01-GAME163-SD-ROOT/sd2snes/fpga_n163.bi3')==(e/'asm/fpga_n163.bi3').read_bytes()
 assert not m['physical_audio'] and not m['continuous_video']
 print('PASS163 evidence/public pins/package',len(files),'files; physical sound pending')
if __name__=='__main__':main()
