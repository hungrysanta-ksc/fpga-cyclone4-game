# SPDX-License-Identifier: MIT
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,sha
from probe_nes_refill267 import run
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'src/fpga/nes_context375/nes_host_context375.sv',d/'nes_host_context375.sv');shutil.copyfile(ROOT/'tools/nes_context375_tb.sv',d/'test.sv')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_host_context375.sv','test.sv'],d,'vlog')
 for case in range(8):
  out=run(q/'vsim.exe',['-c','context375_tb',f'-gCASE={case}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'case{case}',120);assert f'PASS CONTEXT375 case={case}' in out
 r=dict(passed=True,cases=8,source={n:sha(d/n) for n in ('nes_host_context375.sv','test.sv')});(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
