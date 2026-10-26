# SPDX-License-Identifier: MIT
"""Test selected375 mapper-facing capacities,not a new MMC4/MMC5 implementation."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 reference=BASE/'probes/nes-context375/map03'
 names=('nes_native_planes165.sv','nes_native_compact181.sv','nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv')
 for n in names:shutil.copyfile(reference/n,d/n)
 shutil.copyfile(ROOT/'tools/nes_mapper376_tb.sv',d/'test.sv');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'test.sv'],d,'vlog')
 cases=[]
 for case in range(6):
  out=run(q/'vsim.exe',['-c','mapper376_tb',f'-gCASE={case}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'case{case}',120)
  assert f'PASS MAPPER376 case={case}' in out and 'Errors: 0, Warnings: 0' in out
  cases.append(dict(case=case,passed=True,raw_log=sha(d/f'case{case}.log')))
 result=dict(passed=True,cases=cases,actual_inputs={n:sha(d/n) for n in (*names,'test.sv')},
  scope='Resolved physical fetch replay/per8pixel palette/full224row split exception stress and plan tag bounds;no live mapper/IRQ/audio/ExRAM implementation or timing gain.')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
