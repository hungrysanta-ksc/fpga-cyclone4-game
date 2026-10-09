# SPDX-License-Identifier: MIT
"""Re-audit same-clock/reset paths on the new126 fit and inspect all reports."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_cdc125_sta import ROOT,sha,put
from verify_nes_control126 import inspect

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args()
 o=a.out;c=o/'candidate';assert not (c/'audit126.log').exists()
 assert sha(c/'audit124.tcl')==sha(ROOT/'tools/nes_reset124_audit.tcl')
 shutil.copy2(__file__,o/'executed-review126.py')
 with (c/'audit126.log').open('wb') as log:
  r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','audit124.tcl'],cwd=c,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 assert r.returncode==0
 result=inspect(o);put(o/'review126.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
