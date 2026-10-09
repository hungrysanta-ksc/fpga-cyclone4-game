# SPDX-License-Identifier: MIT
"""Copy the selected131 routed DB and inventory current cross-clock endpoints."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_loader127 import ROOT,sha,put

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-counter131/evidence';o=a.out.resolve()
 assert not o.exists() and str(o).isascii()
 meta=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 for n,h in pins.items():
  if n.startswith('fit05/'):
   assert sha(e/n)==h,n;inputs[n[len('fit05/'):]]=h
 shutil.copytree(e/'fit05',o)
 put(o/'inputs132.json',json.dumps(dict(source_manifest=meta['manifest_sha256'],files=inputs,new_map=False,new_fit=False),indent=2)+'\n')
 shutil.copy2(__file__,o/'executed-inventory132.py')
 s=(ROOT/'tools/nes_cdc125_inventory.tcl').read_text().replace('inventory125.tsv','inventory132.tsv')
 put(o/'inventory132.tcl',s)
 with (o/'inventory132.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','inventory132.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 print('PASS132 copied131 routing; cross-clock inventory generated, not yet classified')
if __name__=='__main__':main()
