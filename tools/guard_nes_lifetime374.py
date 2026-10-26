# SPDX-License-Identifier: MIT
"""Two-bank lifetime,drained retire,BG partial,STOP and generation guards."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'src/fpga/nes_native374/nes_plan_batch206.sv',d/'nes_plan_batch206.sv')
 for n in ('nes_domain_reset124.sv','nes_native_mailbox206.sv'):shutil.copyfile(BASE/'probes/nes-dual373/map03'/n,d/n)
 shutil.copyfile(ROOT/'tools/nes_lifetime374_tb.sv',d/'test.sv')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_plan_batch206.sv','nes_domain_reset124.sv','nes_native_mailbox206.sv','test.sv'],d,'vlog')
 cases=[]
 for i in range(6):
  out=run(q/'vsim.exe',['-L','altera_mf_ver','-c','lifetime374_tb',f'-gCASE={i}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'case{i}',120)
  assert f'PASS LIFETIME374 case={i}' in out;cases.append(i)
 result=dict(passed=True,cases=cases,actual_inputs={n:sha(d/n) for n in ('nes_plan_batch206.sv','nes_domain_reset124.sv','nes_native_mailbox206.sv','test.sv')},vendor_model='altera_mf_ver.altsyncram')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
