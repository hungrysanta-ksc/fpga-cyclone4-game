# SPDX-License-Identifier: MIT
"""New physical SNES bus plus actual135 core/reader/encoder/transport integration."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_screen137 import ROOT,put,sha
from nes_fault139 import prepare
import re
from nes_functional import VHDL
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;prepare(a.baseline,o,'fit');names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(o/'board.qsf').read_text())
 assert os.environ.get('SALT_LICENSE_SERVER','') in ['18000@localhost','18000@127.0.0.1']
 for n in ['run133_pll_model.sv','fault139_tb.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 shutil.copy2(a.baseline/'nes-command135/evidence/fit03/rom_boot_model.sv',o/'rom_boot_model.sv')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 sv=[n for n in names if n not in VHDL and n not in ['nes_clock_pll123.v','fxpak_nes_screen137_top.sv','nes_screen_bus137.sv']]
 run('vlog',['-sv','-mfcu',*sv,'run133_pll_model.sv','nes_screen_bus137.sv','fxpak_nes_screen137_top.sv','rom_boot_model.sv','fault139_tb.sv'],'compile')
 run('vsim',['-c','fault139_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
 log=(o/'simulation.log').read_text(errors='replace');assert 'PASS139 first-fault' in log and '** Fatal:' not in log
 put(o/'result.json',json.dumps(dict(passed=True,scope='5B/D6 actual core seeded normal RUN, first CPU deadline edge, two-page read and retention across STOP/second event; no physical claim.',physical=False),indent=2)+'\n')
 print('PASS139 first-fault actual core /5B D6/ROM/STOP')
if __name__=='__main__':main()
