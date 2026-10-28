# SPDX-License-Identifier: MIT
"""Materialize a reproducible candidate from the392 source boundary."""
import argparse,shutil
from pathlib import Path
from nes_delta231 import BASE
from nes_jobs394 import arm,rtl
from nes_source368 import compile_arm

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--cold-quantum',type=int,choices=(0,256),default=0);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 source=BASE/'probes/nes-plan390/joint04'
 for f in source.iterdir():
  if f.is_file()and f.suffix in('.sv','.c','.h','.inc','.s','.a','.ld'):shutil.copyfile(f,d/f.name)
 arm(d,a.cold_quantum);rtl(d);compile_arm(d)
 print((d/'size368.log').read_text())
if __name__=='__main__':main()
