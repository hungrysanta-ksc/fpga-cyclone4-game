# SPDX-License-Identifier: MIT
"""Inspect the existing135 board routing; never run MAP/FIT or edit its archive."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-command135/evidence';o=a.out.resolve()
 assert not o.exists() and str(o).isascii()
 m=json.loads((ROOT/'analysis/command135-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 for n,h in pins.items():
  if n.startswith('fit03/'):assert sha(e/n)==h,n;inputs[n[6:]]=h
 shutil.copytree(e/'fit03',o)
 put(o/'inputs136.json',json.dumps(dict(source_manifest=m['manifest_sha256'],files=inputs,new_map=False,new_fit=False),indent=2)+'\n')
 shutil.copy2(__file__,o/'executed-inventory136.py')
 s=(ROOT/'tools/nes_cdc125_inventory.tcl').read_text().replace('project_open live','project_open board').replace('inventory125.tsv','inventory136.tsv')
 put(o/'inventory136.tcl',s)
 with (o/'inventory136.log').open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','inventory136.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 print('PASS136 copied135 fit03 routing; current crossing inventory available')
if __name__=='__main__':main()
