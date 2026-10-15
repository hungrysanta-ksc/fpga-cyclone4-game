# SPDX-License-Identifier: MIT
"""Integrate the verified map185 candidate into the full184 firmware tree."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_board181 import copy_pins

def prepare(prior,candidate,out):
 p=json.loads((prior/'preparation-window184-trial.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);changed={};candidate_pins={}
 for f in sorted(candidate.iterdir()):
  if f.suffix not in ('.c','.h'):continue
  n='src/'+f.name;assert n in pins,n
  candidate_pins[f.name]=sha(f)
  if sha(out/n)!=sha(f):(out/n).write_bytes(f.read_bytes());changed[n]=sha(out/n)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-184','NES-GAME-185'),('GAME 184','GAME 185'),('game184.nes','game185.nes'),('fpga_n184.bi3','fpga_n185.bi3'),('last-184.txt','last-185.txt'),('NES184 seq=','NES185 seq='),('nes-progress-184.txt','nes-progress-185.txt'),('NES-GAME184-DEV','NES-GAME185-DEV')]:s=s.replace(a,b)
  (out/n).write_text(s,encoding='utf8',newline='\n');changed[n]=sha(out/n)
 r=dict(copied=pins,changed=changed,added={},candidate_pins=candidate_pins,hardware_package=False,baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_paired185.py','tools/nes_map185.py','tools/nes_pad185.py']})
 for n in ['preparation-paired185.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','candidate','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.candidate,a.out)['changed']))
