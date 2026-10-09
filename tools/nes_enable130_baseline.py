# SPDX-License-Identifier: MIT
"""Copy the pinned129 fitted DB before read-only state-port inspection."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_enable130 import ROOT,sha,put
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii();o.mkdir()
 e=a.baseline/'nes-reader129/evidence';m=json.loads((ROOT/'analysis/reader129-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 for n,h in pins.items():
  if n.startswith('fit01/'):
   src=e/n;assert sha(src)==h;rel=n[len('fit01/'):];dst=o/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[rel]=h
 shutil.copy2(ROOT/'tools/nes_enable130_paths.tcl',o/'state130.tcl')
 with (o/'state130.log').open('wb') as log:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','state130.tcl'],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0
 put(o/'baseline130.json',json.dumps(dict(inputs=inputs,source_manifest=m['manifest_sha256'],new_fit=False),indent=2)+'\n');print('PASS130 baseline port audit on copied129 fitted DB')
if __name__=='__main__':main()
