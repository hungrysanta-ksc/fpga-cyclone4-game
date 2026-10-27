# SPDX-License-Identifier: MIT
import argparse,shutil
from pathlib import Path
from nes_delta231 import BASE
from nes_joint398 import arm,rtl,ea_only
from nes_source368 import compile_arm
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--variant',choices=('joint','ea-only'),default='joint');a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for f in(BASE/'probes/nes-plan390/joint04').iterdir():
  if f.is_file()and f.suffix in('.sv','.c','.h','.inc','.s','.a','.ld'):shutil.copyfile(f,d/f.name)
 arm(d);(rtl if a.variant=='joint'else ea_only)(d);compile_arm(d);print((d/'size368.log').read_text())
if __name__=='__main__':main()
