# SPDX-License-Identifier: MIT
"""Names/history label only; reuse174 runtime, wire reader, SNES and stack."""
from pathlib import Path
import argparse,json
from nes_game147 import sha
from nes_snapshot175_mcu import prepare as previous

def prepare(prior,out):
 r=previous(prior,out)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text().replace('175','177').replace('LAST16_NATIVE_STATE_A5','LAST16_BOUNDARY177_LOW22')
  (out/n).write_text(s,encoding='utf8',newline='\n');r['changed'][n]=sha(out/n)
 assert (out/'src/nes_run136.inc').read_bytes()==(prior/'src/nes_run136.inc').read_bytes()
 r['history_schema']='177: upper74 legacy, low22 tag6/state4/flags14'
 r['public_sources']['tools/nes_boundary177_mcu.py']=sha(Path(__file__))
 for n in ['preparation-boundary177.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.prior,a.out)
