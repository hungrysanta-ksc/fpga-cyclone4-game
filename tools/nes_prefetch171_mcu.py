# SPDX-License-Identifier: MIT
"""171 identity only;170 transport, timers, diagnostics and safety unchanged."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha
def prepare(prior,out):
 assert not out.exists();out.mkdir(parents=True)
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='12220e2921e63d123d430dbca6f6d8172a13094349ef28df225850778950ffec'
 m=json.loads((prior/'preparation-startup170.json').read_bytes());pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,p);r['copied'][n]=h
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  p=out/n;s=p.read_text();t=s
  for a,b in [('NES-GAME-170','NES-GAME-171'),('GAME 170','GAME 171'),('game170.nes','game171.nes'),('fpga_n170.bi3','fpga_n171.bi3'),('last-170.txt','last-171.txt'),('NES170 seq=','NES171 seq='),('nes-progress-170.txt','nes-progress-171.txt'),('NES-GAME170-DEV','NES-GAME171-DEV')]:t=t.replace(a,b)
  assert t!=s,n;p.write_text(t,encoding='utf-8',newline='\n');r['changed'][n]=sha(p)
 for n in ['preparation-prefetch171.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.prior,a.out)
