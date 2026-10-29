# SPDX-License-Identifier: MIT
"""Run 227 FatFS/config programmer on a selected diagnostic BI3/RBF pair."""
import argparse,json,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--image',required=True,type=Path);p.add_argument('--rbf',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();image=a.image.resolve();rbf=a.rbf.resolve();assert image.is_file() and rbf.is_file()
s=(ROOT/'tools/test_nes_nrom423_programmer.py').read_text(encoding='utf-8')
def once(s,x,y):assert s.count(x)==1;return s.replace(x,y,1)
s=once(s,"BASE/'probes/nes-nrom423/asm01/fpga_nrom16.bi3'",'Path('+repr(str(image))+')')
s=once(s,"BASE/'probes/nes-nrom423/asm01/board.rbf'",'Path('+repr(str(rbf))+')')
s=once(s,"'scope':'actual programmer/FatFS with exact diagnostic BI3 and modeled GPIO/DONE; not FPGA hardware'","'scope':'actual 227 programmer/FatFS with selected diagnostic BI3/RBF and modeled GPIO/DONE; not physical reconfiguration or base token'")
sys.argv=['test_nes_nrom423_programmer.py','--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/test_nes_nrom423_programmer.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom423_programmer.py')})
r=json.loads((a.out/'result.json').read_text());assert r['passed'] and r['image_sha256']==sha(image) and r['rbf_sha256']==sha(rbf)
