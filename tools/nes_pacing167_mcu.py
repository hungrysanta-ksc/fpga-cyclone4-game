# SPDX-License-Identifier: MIT
"""167 paths only over166. Trace reason byte now carries fill<<4|export."""
from pathlib import Path
import argparse,json,difflib
from nes_game147 import sha
from nes_trace166 import prepare as parent
def prepare(evidence,out):
 p=parent(evidence,out);diff=[]
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  f=out/n;old=f.read_text();s=old
  for a,b in [('NES-GAME-166','NES-GAME-167'),('GAME 166','GAME 167'),('game166.nes','game167.nes'),('fpga_n166.bi3','fpga_n167.bi3'),('last-166.txt','last-167.txt'),('NES166 seq=','NES167 seq='),('nes-progress-166.txt','nes-progress-167.txt'),('NES-GAME166-DEV','NES-GAME167-DEV')]:s=s.replace(a,b)
  assert old!=s;nkey='added' if n in p['added'] else 'changed';f.write_text(s,encoding='utf8',newline='\n');p[nkey][n]=sha(f)
  diff.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='166/'+n,tofile='167/'+n))
 p['scope']='Only167 paths/version over166; unchanged48B trace records raw ABORT byte: export low4, fill detail high4. Original74 SPI ID/receiver remain compatible; install paired167 FPGA.'
 for n in ['preparation-runlease165.json','preparation-pacing167.json']:(out/n).write_text(json.dumps(p,indent=2)+'\n')
 (out/'changes-pacing167.diff').write_text(''.join(diff),encoding='utf8',newline='\n')
 return p
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.evidence,a.out)
