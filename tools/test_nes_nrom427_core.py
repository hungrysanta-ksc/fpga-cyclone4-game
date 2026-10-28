# SPDX-License-Identifier: MIT
"""Capture one actual board geometry block from the 424 ROM, seeded load."""
import argparse,json,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
s=(ROOT/'tools/test_nes_nrom426_core.py').read_text()
def once(s,x,y):assert s.count(x)==1,(x,s.count(x));return s.replace(x,y)
s=once(s,"ROOT/'tests/nes-nrom426/core_tb.sv'","ROOT/'tests/nes-nrom427/core_tb.sv'")
s=once(s,"assert 'PASS NROM426 actual seeded NROM core pixel' in log and 'Errors: 0' in log", "assert 'PASS NROM426 actual seeded NROM core pixel' in log and 'PASS NROM427 geometry first block' in log and 'Errors: 0' in log")
s=once(s,"'scope':'actual 227 board/NES core and NROM mapper, seeded PSRAM/verified loader, manual SNES bus program read and pad writes, core pixels and SPI STOP; not actual loader, 65816 execution, actual controller or hardware'", "'scope':'actual 227 board/NES core and first geometry D0/D1 CRC/D2, seeded PSRAM/verified loader and manually driven SNES bus; not complete geometry, actual ARM, 65816 execution or hardware'")
sys.argv=['test_nes_nrom426_core.py','--board',str(a.board),'--rom',str(a.rom),'--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/test_nes_nrom426_core.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom426_core.py')})
r=json.loads((a.out/'result.json').read_text());block=a.out/'nrom427-block.hex';r['geometry_block_sha256']=sha(block);r['geometry_bytes']=len(bytes.fromhex(block.read_text()));assert 1<=r['geometry_bytes']<=256
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
