# SPDX-License-Identifier: MIT
"""Verify frozen164 evidence, source pins and install pair without rebuilding."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game164-verification.json').read_bytes());e=a.baseline/'nes-game164/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['client','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 asm=json.loads((e/'asm/result164.json').read_bytes());assert asm['passed'] and not asm['new_map_fit']
 assert sha(e/'asm/game-program.hex')==asm['program_sha256']==json.loads((e/'client/result.json').read_bytes())['program_sha256']
 for n,h in asm['unchanged_routing_and_sources'].items():assert sha(e/'asm'/n)==h,n
 assert sha(e/'asm'/asm['generated_mif'])==asm['mif_sha256']
 zpath=e/'release/NES164-SMB3-VBLANK-VIDEO.zip';assert sha(zpath)==m['package']['zip_sha256']
 with zipfile.ZipFile(zpath) as z:
  assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game164-instructions.ko.md').read_bytes()
  assert z.read('01-GAME164-SD-ROOT/sd2snes/firmware.stm')==(e/'arm/src/obj-nes-100/firmware.stm').read_bytes()
  assert z.read('01-GAME164-SD-ROOT/sd2snes/fpga_n164.bi3')==(e/'asm/fpga_n164.bi3').read_bytes()
  d=json.loads(z.read('decision164.json'));assert not d['post_reveal_forced_blank'] and not d['atomic_frame_flip'] and not d['smooth_60fps']
 assert m['physical_video_pending']
 print('PASS164 evidence/public pins/package',len(files),'files; physical video pending')
if __name__=='__main__':main()
