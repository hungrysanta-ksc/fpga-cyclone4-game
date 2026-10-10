# SPDX-License-Identifier: MIT
"""Collect same-clock and crossing reports from an isolated140 fit copy."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['fit','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 pins={f.relative_to(a.fit).as_posix():sha(f) for f in a.fit.rglob('*') if f.is_file()}
 shutil.copytree(a.fit,a.out)
 for name,source in [('timing140','nes_board134_timing.tcl'),('inventory140','nes_cdc125_inventory.tcl')]:
  s=(ROOT/'tools'/source).read_text().replace('project_open live','project_open board').replace('134','140').replace('inventory125.tsv','inventory140.tsv')
  (a.out/(name+'.tcl')).write_text(s,encoding='utf8',newline='\n')
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t',name+'.tcl'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,name
 for n,h in pins.items():assert sha(a.fit/n)==h,n
 (a.out/'inputs140.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,a.out/'executed-inventory140.py')
 print('PASS140 same fit routing inspected')
if __name__=='__main__':main()
