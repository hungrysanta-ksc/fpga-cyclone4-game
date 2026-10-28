# SPDX-License-Identifier: MIT
"""Directed373 ownership, FIFO, SPI, STOP and final input-ACK fault guards."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_refill267 import run
from nes_dual373 import DIRECTORY

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for n in ('nes_native_capture365.sv','nes_transport257.sv','nes_spi270.sv'):shutil.copyfile(DIRECTORY/n,d/n)
 shutil.copyfile(BASE/'probes/nes-source368/map01/nes_native_mailbox206.sv',d/'nes_native_mailbox206.sv')
 for n in ('nes_context373_tb.sv','nes_ring373_tb.sv'):shutil.copyfile(ROOT/'tools'/n,d/n)
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib')
 run(q/'vlog.exe',['-sv','nes_native_mailbox206.sv','nes_native_capture365.sv','nes_transport257.sv','nes_spi270.sv','nes_context373_tb.sv','nes_ring373_tb.sv'],d,'vlog')
 passed=[]
 for module,count in (('context373_tb',5),('ring373_tb',9)):
  for case in range(count):
   label=f'{module}-{case}'
   out=run(q/'vsim.exe',['-c',f'work.{module}',f'-gCASE={case}','-do','onerror {quit -code 1};run -all;quit -f'],d,label,120)
   assert f'PASS {"CONTEXT373" if module.startswith("context") else "RING373"} case={case}' in out
   passed.append(label)
 result=dict(passed=True,cases=passed,source_hashes={f.name:sha(f) for f in d.glob('*.sv')},collector_stub=True)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
