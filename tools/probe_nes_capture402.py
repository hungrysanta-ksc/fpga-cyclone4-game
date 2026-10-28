# SPDX-License-Identifier: MIT
"""Differential full-frame capture, consecutive same-rank and STOP/restart."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_refill267 import run
from nes_capture402 import apply

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 apply(d);s=(BASE/'probes/nes-joint400/map01/nes_native_compact181.sv').read_text().replace('module nes_native_compact181(', 'module nes_native_compact402_reference(')
 (d/'reference.sv').write_text(s,newline='\n');shutil.copyfile(ROOT/'tests/nes-joint402/capture_tb.sv',d/'capture_tb.sv')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_native_compact181.sv','reference.sv','capture_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.capture402_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120)
 assert 'PASS CAPTURE402 frames=5'in log
 (d/'result.json').write_text(json.dumps(dict(passed=True,scope=__doc__,files={q.name:sha(q)for q in d.glob('*.sv')}),indent=2)+'\n',newline='\n');print(log[-1000:])
if __name__=='__main__':main()
