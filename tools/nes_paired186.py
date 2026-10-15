# SPDX-License-Identifier: MIT
"""Integrate the verified map186 candidate into the full185 firmware tree."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_board181 import copy_pins

def prepare(prior,candidate,out):
 p=json.loads((prior/'preparation-paired185.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);changed={};candidate_pins={}
 for f in sorted(candidate.iterdir()):
  if f.suffix not in ('.c','.h'):continue
  n='src/'+f.name;assert n in pins,n
  candidate_pins[f.name]=sha(f)
  if sha(out/n)!=sha(f):(out/n).write_bytes(f.read_bytes());changed[n]=sha(out/n)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-185','NES-GAME-186'),('GAME 185','GAME 186'),('game185.nes','game186.nes'),('fpga_n185.bi3','fpga_n186.bi3'),('last-185.txt','last-186.txt'),('NES185 seq=','NES186 seq='),('nes-progress-185.txt','nes-progress-186.txt'),('NES-GAME185-DEV','NES-GAME186-DEV')]:s=s.replace(a,b)
  (out/n).write_text(s,encoding='utf8',newline='\n');changed[n]=sha(out/n)
 r=dict(copied=pins,changed=changed,added={},candidate_pins=candidate_pins,hardware_package=False,baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_paired186.py','tools/nes_copy186.py','tools/nes_pad185.py']})
 for n in ['preparation-paired186.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','candidate','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.candidate,a.out)['changed']))
