# SPDX-License-Identifier: MIT
"""Reproduce stale142 observer data under explicit delayed-input stimulus."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_spi_boot import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 shutil.copy2(a.candidate/'nes_screen_status142.sv',o/'nes_screen_status142.sv')
 shutil.copy2(ROOT/'tests/nes-functional/screen144_status_late_tb.sv',o/'screen144_status_late_tb.sv')
 for exe,args in [('vlib',['work']),('vlog',['-sv','nes_screen_status142.sv','screen144_status_late_tb.sv']),('vsim',['-c','screen144_status_late_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (o/(exe+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(o/(exe+'.log')).read_text(errors='replace');assert not r.returncode and '** Fatal:' not in s,(exe,s[-1000:])
 assert 'PASS144 stale-stage reproduction' in s
 (o/'result.json').write_text(json.dumps(dict(passed=True,source_sha256=sha(o/'nes_screen_status142.sv'),on_time_control=True,late_stage63_observed70=True,late_stage31_observed70=True,physical_root_cause_confirmed=False,scope='80ns input delay deliberately injected after WR assertion; demonstrates first stable pair can latch stale bus value. No physical delay measurement, no RTL fix or timing claim.'),indent=2)+'\n')
 print('PASS144 observer hypothesis reproduced; not physical root-cause proof')
if __name__=='__main__':main()
