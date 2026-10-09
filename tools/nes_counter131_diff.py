# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_counter131 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','baseline']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii();o.mkdir()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 materialize(o,a.baseline)
 original=a.baseline/'nes-enable130/evidence/fit01/nes_rom_loader.sv'
 pins=json.loads((a.baseline/'nes-enable130/evidence/manifest.json').read_bytes())['files'];assert sha(original)==pins['fit01/nes_rom_loader.sv']
 put(o/'reference127.sv',original.read_text().replace('module nes_rom_loader #','module nes_rom_loader_reference #'))
 shutil.copy2(ROOT/'tests/nes-functional/counter131_diff_tb.sv',o/'counter131_diff_tb.sv');shutil.copy2(__file__,o/'executed-diff.py')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_loader.sv','reference127.sv','counter131_diff_tb.sv'],'compile')
 run('vsim',['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'diff')
 log=(o/'diff.log').read_text();assert 'PASS131 DIFF one_step_cases=26112' in log and '** Fatal:' not in log
 s=(o/'nes_rom_loader.sv').read_text();needle="else if(!timed_phase)remaining<=CW'(SETUP_CYCLES);";assert needle in s
 put(o/'negative-preload.sv',s.replace(needle,"else if(!timed_phase)remaining<=CW'(SETUP_CYCLES-1);",1))
 run('vlog',['-sv','negative-preload.sv'],'negative-compile');run('vsim',['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative')
 assert '** Fatal: DIFF131' in (o/'negative.log').read_text()
 put(o/'diff131.json',json.dumps(dict(passed=True,one_step_cases=26112,negative_preload_rejected=True,sources={p.name:sha(p) for p in o.iterdir() if p.suffix in ['.sv','.py']}),indent=2)+'\n');print('PASS128 actual130/131 observable state-step differential + preload mutation')
if __name__=='__main__':main()
