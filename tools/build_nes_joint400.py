# SPDX-License-Identifier: MIT
import argparse,shutil
from pathlib import Path
from nes_delta231 import BASE
from nes_joint398 import arm,rtl
from nes_overlap400 import apply
from nes_fixed400 import apply as fixed
from nes_source368 import compile_arm
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for q in(BASE/'probes/nes-plan390/joint04').iterdir():
  if q.is_file()and q.suffix in('.sv','.c','.h','.inc','.s','.a','.ld'):shutil.copyfile(q,d/q.name)
 arm(d);apply(d);rtl(d);fixed(d);compile_arm(d);print((d/'size368.log').read_text())
if __name__=='__main__':main()
