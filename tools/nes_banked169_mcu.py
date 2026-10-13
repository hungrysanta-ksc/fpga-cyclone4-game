# SPDX-License-Identifier: MIT
"""169 pair naming only; retain168 MCU execution and first-failure telemetry."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import sha
def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='111a28c43966b0659f65743b3a46b403712b40520aeebd37d1301d2a78856dda'
 out.mkdir(parents=True,exist_ok=False);m=json.loads((prior/'preparation-sink168.json').read_bytes());pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,d);r['copied'][n]=h
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  f=out/n;s=f.read_text();t=s
  for a,b in [('NES-GAME-168','NES-GAME-169'),('GAME 168','GAME 169'),('game168.nes','game169.nes'),('fpga_n168.bi3','fpga_n169.bi3'),('last-168.txt','last-169.txt'),('NES168 seq=','NES169 seq='),('nes-progress-168.txt','nes-progress-169.txt'),('NES-GAME168-DEV','NES-GAME169-DEV')]:t=t.replace(a,b)
  assert s!=t,n;f.write_text(t,encoding='utf8',newline='\n');r['changed'][n]=sha(f)
 for name in ['preparation-banked169.json','preparation-runlease165.json']:(out/name).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.prior,a.out)
