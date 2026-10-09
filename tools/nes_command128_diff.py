# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_command128 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','baseline']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii();o.mkdir()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 materialize(o,a.baseline)
 original=a.baseline/'nes-loader127/evidence/fit02/nes_rom_loader.sv'
 pins=json.loads((a.baseline/'nes-loader127/evidence/manifest.json').read_bytes())['files'];assert sha(original)==pins['fit02/nes_rom_loader.sv']
 put(o/'reference127.sv',original.read_text().replace('module nes_rom_loader #','module nes_rom_loader_reference #'))
 shutil.copy2(ROOT/'tests/nes-functional/loader128_diff_tb.sv',o/'loader128_diff_tb.sv');shutil.copy2(__file__,o/'executed-diff.py')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_loader.sv','reference127.sv','loader128_diff_tb.sv'],'compile')
 run('vsim',['-c','loader128_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'diff')
 log=(o/'diff.log').read_text();assert 'PASS128 DIFF one_step_cases=26112' in log and '** Fatal:' not in log
 s=(o/'nes_rom_loader.sv').read_text();needle='else if(load_end)fail(2);';assert needle in s
 put(o/'negative-error-priority.sv',s.replace(needle,'else if(load_end)fail(3);',1))
 run('vlog',['-sv','negative-error-priority.sv'],'negative-compile');run('vsim',['-c','loader128_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative')
 assert '** Fatal: DIFF128' in (o/'negative.log').read_text()
 put(o/'diff128.json',json.dumps(dict(passed=True,one_step_cases=26112,negative_error_code_rejected=True,sources={p.name:sha(p) for p in o.iterdir() if p.suffix in ['.sv','.py']}),indent=2)+'\n');print('PASS128 actual127/128 state-step differential + error-code mutation')
if __name__=='__main__':main()
