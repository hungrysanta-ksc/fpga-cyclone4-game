# SPDX-License-Identifier: MIT
"""Prepare217 identity only; preserve215 runtime/diagnostics and60s guard."""
from pathlib import Path
import argparse,json
from nes_runtime213 import ROOT,BASE,sha
from nes_board181 import copy_pins
def prepare(out):
 prior=BASE/'probes/nes-plan215/arm01';p=json.loads((prior/'preparation-plan215.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins)
 for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  f=out/'src'/name;s=f.read_text()
  for x,y in [('NES-GAME-215','NES-GAME-217'),('GAME 215','GAME 217'),('game215.nes','game217.nes'),('fpga_n215.bi3','fpga_n217.bi3'),('last-215.txt','last-217.txt'),('NES215','NES217'),('nes-progress-215.txt','nes-progress-217.txt'),('nes-budget-215.txt','nes-budget-217.txt'),('NES-GAME215-DEV','NES-GAME217-DEV')]:s=s.replace(x,y)
  f.write_text(s,encoding='utf8')
 changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
 assert set(changed)=={'src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'}
 r=dict(copied=pins,changed=changed,added={},public_sources={'tools/nes_loader217_arm.py':sha(Path(__file__))},runtime_unchanged215=True,budget_schema=215,new_fpga=True,physical=False)
 (out/'preparation-loader217.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(changed))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
