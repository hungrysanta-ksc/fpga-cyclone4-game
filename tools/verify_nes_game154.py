# SPDX-License-Identifier: MIT
"""Verify frozen154 evidence and paired artifacts without rebuilding old work."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game154-verification.json').read_bytes());e=a.baseline/'nes-game154/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['host','decoder','observer']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 assert json.loads((e/'armcheck/result.json').read_bytes())['strong_nmi']
 assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
 assert sha(e/'release/NES154-SMB3-PPU-STATE.zip')==m['package']['zip_sha256']
 assert sha(e/'asm/fpga_n154.bi3')==m['package']['fpga_sha256']
 assert sha(e/'arm/src/obj-nes-100/firmware.stm')==m['package']['firmware_sha256']
 old=a.baseline/'nes-game152/evidence'
 assert sha(e/'asm/nes_rom_service.sv')==sha(old/'asm/nes_rom_service.sv')
 assert not m['ppu_deadline_fixed'] and not m['physical_test']
 print('PASS154 integrity; supplemental state/recovery model verified; physical PPU cause remains open')
if __name__=='__main__':main()
