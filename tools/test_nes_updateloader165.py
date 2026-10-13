# SPDX-License-Identifier: MIT
"""Old/new loader comparison: all state codes, command priorities, timed writes."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_update165 import loader as transform
from test_nes_drain165 import bench as old_bench

from test_nes_state165 import bench as prior_bench
def bench():
 s=prior_bench().replace('dut.remaining=remaining;', 'dut.remaining=remaining;dut.terminal=(remaining==1);')
 s=s.replace(' initial begin\n', ' always @(posedge mem_clk or posedge reset)begin #0.002; if(dut.terminal!==(dut.remaining==1))$fatal(1,"UPDATE165 terminal invariant");end\n initial begin\n',1)
 return s


def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.prepared/'nes_rom_loader.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'candidate.sv').write_text(new)
 (a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1))
 (a.out/'state165_tb.sv').write_text(bench())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert ('** Fatal: DIFF131' in log or '** Fatal: UPDATE165 terminal invariant' in log) and 'PASS STATE165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','state165_tb.sv'],'compile')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'equivalence');assert 'PASS STATE165 states=294912 sequences=1056' in log
 needle='terminal<=(remaining==2)';assert new.count(needle)==1
 (a.out/'wrong-terminal.sv').write_text(new.replace(needle,'terminal<=(remaining==1)'))
 run('vlog',['-sv','wrong-terminal.sv'],'negative-compile')
 log=run('vsim',args,'negative',True)
 r=dict(passed=True,states=294912,sequences=1056,all_state_codes=16,remaining_cases=[0,1,2,22,64,127],wrong_terminal_rejected=True,terminal_invariant_checked=True,
  source_sha256=sha(a.prepared/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),
  scope='One-step seeded old-register/pin comparison, followed by actual single-byte writes with eight command/reset actions over132 phases. Not whole-ROM load or gameplay.',
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_update165.py','tools/test_nes_updateloader165.py','tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
