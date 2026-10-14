# SPDX-License-Identifier: MIT
"""170 transport failure boundary; retain169 FPGA/SNES and all RUN decisions."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha
def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='70a5edc665a74fff59fc384c8011a858becd3f834405349d400a341106df0282'
 assert not out.exists();out.mkdir(parents=True)
 m=json.loads((prior/'preparation-banked169.json').read_bytes());pins=m['copied']|m['changed']|m['added'];r=dict(copied={},changed={},added={})
 for n,h in pins.items():
  assert sha(prior/n)==h,n
  d=out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prior/n,d);r['copied'][n]=h
 def put(n,s):
  (out/n).write_text(s,encoding='utf8',newline='\n');r['changed' if n in pins else 'added'][n]=sha(out/n)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text();t=s
  for a,b in [('NES-GAME-169','NES-GAME-170'),('GAME 169','GAME 170'),('game169.nes','game170.nes'),('fpga_n169.bi3','fpga_n170.bi3'),('last-169.txt','last-170.txt'),('NES169 seq=','NES170 seq='),('nes-progress-169.txt','nes-progress-170.txt'),('NES-GAME169-DEV','NES-GAME170-DEV')]:t=t.replace(a,b)
  assert t!=s,n
  if n.endswith('nes_menu_diagnostic.c'):
   t=t.replace('#include "nes_sink_trace168.h"','#include "nes_sink_trace168.h"\n#include "nes_sink_io170.h"')
   t=t.replace('memset(&nes_sink_trace168,0,sizeof(nes_sink_trace168));','memset(&nes_sink_trace168,0,sizeof(nes_sink_trace168));\n memset(&nes_sink_io170,0,sizeof(nes_sink_io170));')
   t=t.replace('n+=extra;\n printf','n+=extra;\n extra=nes_sink_io170_format(text+n,4096-(unsigned)n);\n if(extra<0)return;\n n+=extra;\n printf')
  put(n,t)
 put('src/nes_sink_spi165.c',(ROOT/'src/nes/firmware/nes_sink_spi170.c').read_text())
 for n in ['nes_sink_io170.c','nes_sink_io170.h']:put('src/'+n,(ROOT/'src/nes/firmware'/n).read_text())
 s=(out/'src/Makefile').read_text();assert s.count('nes_sink_trace168.c')==1
 put('src/Makefile',s.replace('nes_sink_trace168.c','nes_sink_trace168.c nes_sink_io170.c'))
 for n in ['preparation-startup170.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.prior,a.out)
