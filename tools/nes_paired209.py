# SPDX-License-Identifier: MIT
"""Give the unchanged203 direct RUN a distinct hardware trial identity.
Add bounded post-STOP plan status to the existing report, not live SD writes.
Preparation alone is not install/package approval.
"""
from pathlib import Path
import argparse,json
from nes_board204 import ROOT,BASE,sha,replace
from nes_board181 import copy_pins

def prepare(out):
 prior=BASE/'probes/nes-metadata203/arm01'
 p=json.loads((prior/'preparation-metadata203.json').read_bytes());pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);changed={}
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-186','NES-GAME-209'),('GAME 186','GAME 209'),('game186.nes','game209.nes'),('fpga_n186.bi3','fpga_n209.bi3'),('last-186.txt','last-209.txt'),('NES186 seq=','NES209 seq='),('nes-progress-186.txt','nes-progress-209.txt'),('NES-META203-DEV','NES-GAME209-DEV')]:s=s.replace(a,b)
  if n.endswith('nes_menu_diagnostic.c'):
   needle=' printf("%s",text);'
   extra=''' extra=snprintf(text+n,4096-(unsigned)n,"plan_error=%u\\nplan_sent=%u\\nplan_end=%u\\n",native_runtime165.plan.error,native_runtime165.plan.sent,native_runtime165.plan.finished?1u:0u);
 if(extra<0||(unsigned)extra>=4096-(unsigned)n)return;
 n+=extra;
'''
   s=replace(s,needle,extra+needle)
  (out/n).write_text(s,encoding='utf8',newline='\n');changed[n]=sha(out/n)
 r=dict(copied=pins,changed=changed,added={},runtime203_unchanged=True,hardware_package=False,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_paired209.py']})
 (out/'preparation-paired209.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.out);print(json.dumps(dict(copied=len(r['copied']),changed=r['changed'])))
