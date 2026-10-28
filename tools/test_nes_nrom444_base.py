# SPDX-License-Identifier: MIT
"""Exact 227 programmer against user-provided 044 base image, pins modeled."""
import argparse,sys,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
image=BASE/'probes/nes-offline-sd-received/user-inputs/fpga_base.bi3';raw=BASE/'probes/nes-offline-075/base-expanded.bin'
assert sha(image)=='eff3f675c93a0209caf4987d72e0f277492c3dddc2b4c2aff334a667b4dbfbc7'
s=(ROOT/'tools/test_nes_nrom423_programmer.py').read_text(encoding='utf-8')
def once(s,x,y):assert s.count(x)==1,(x,s.count(x));return s.replace(x,y)
s=once(s,"BASE/'probes/nes-nrom423/asm01/fpga_nrom16.bi3'","BASE/'probes/nes-offline-sd-received/user-inputs/fpga_base.bi3'")
s=once(s,"BASE/'probes/nes-nrom423/asm01/board.rbf'","BASE/'probes/nes-offline-075/base-expanded.bin'")
s=once(s,"'scope':'actual programmer/FatFS with exact diagnostic BI3 and modeled GPIO/DONE; not FPGA hardware'","'scope':'actual 227 programmer/FatFS with user-provided 044 base BI3 and independently preserved 075 expansion, modeled GPIO/DONE; not physical reconfiguration or base token'")
sys.argv=['test_nes_nrom423_programmer.py','--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/test_nes_nrom423_programmer.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom423_programmer.py')})
r=json.loads((a.out/'result.json').read_text());assert r['passed'] and r['image_sha256']==sha(image) and r['rbf_sha256']==sha(raw)
