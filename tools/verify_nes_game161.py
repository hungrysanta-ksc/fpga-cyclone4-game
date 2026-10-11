# SPDX-License-Identifier: MIT
"""Verify immutable161 evidence and exact delivered inputs without rebuilding."""
from pathlib import Path
import argparse,json,zipfile
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
 m=json.loads((ROOT/'analysis/game161-verification.json').read_bytes());e=a.baseline/'nes-game161/evidence'
 assert sha(e/'manifest.json')==m['manifest_sha256'];files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 for n in ['test','cache','client','host','reuse']:assert json.loads((e/n/'result.json').read_bytes())['passed']
 t=json.loads((e/'test/result.json').read_bytes());assert len(t['runs'])==24 and len(t['regression159'])==6
 for n,h in t['sources'].items():assert sha((e/'test' if n.startswith('game') else e/'asm')/n)==h,n
 assert sha(e/'cache/new/nes_rom_service.sv')==sha(e/'asm/nes_rom_service.sv')
 assert sha(e/'cache/new/game161_cache_tb.sv')==sha(ROOT/'tests/nes-functional/game161_cache_tb.sv')
 assert (e/'client/client/game-program.hex').read_bytes()==(e/'asm/game-program.hex').read_bytes()
 assert (e/'asm/nominal156.sdc').read_bytes()==(a.baseline/'nes-game160/evidence/asm/nominal156.sdc').read_bytes()
 assert m['timing']['passed'] and not m['timing']['implementation_budget_passed']
 archive=e/'release/NES161-SMB3-CACHE-HOLD6.zip';assert sha(archive)==m['package']['zip_sha256']
 with zipfile.ZipFile(archive) as z:assert z.read('START-HERE.ko.md')==(ROOT/'docs/nes-game161-instructions.ko.md').read_bytes()
 assert not m['physical_test'] and not m['gameplay_passed'] and m['fit']['m9k']==56
 print('PASS161 frozen evidence/public pins/package:',len(files),'files; cache15/oldcontrol; prior159/160 boundaries; hold6 SNES model')
if __name__=='__main__':main()
