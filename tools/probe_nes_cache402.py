# SPDX-License-Identifier: MIT
"""Cycle-identical cache metadata RAM, six-clock backing reads and STOP drain."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_refill267 import run
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--shared',action='store_true');a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'src/fpga/nes_joint402'/('cache_shared.sv'if a.shared else'nes_chr_cache192.sv'),d/'cache.sv')
 s=(BASE/'probes/nes-joint400/map01/nes_chr_cache192.sv').read_text().replace('module nes_chr_cache192(', 'module nes_chr_cache402_reference(');(d/'reference.sv').write_text(s,newline='\n')
 tb=(ROOT/'tests/nes-joint402/cache_tb.sv').read_text()
 if a.shared:tb=tb.replace('before402[16]','before402[144]').replace('dut.metadata402','dut.storage402').replace('for(integer i=0;i<16;i++)','for(integer i=0;i<144;i++)')
 (d/'cache_tb.sv').write_text(tb,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','cache.sv','reference.sv','cache_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.cache402_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);assert 'PASS CACHE402'in log
 (d/'result.json').write_text(json.dumps(dict(passed=True,scope=__doc__,files={q.name:sha(q)for q in d.glob('*.sv')}),indent=2)+'\n',newline='\n');print(log[-1200:])
if __name__=='__main__':main()
