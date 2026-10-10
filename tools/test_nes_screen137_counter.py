# SPDX-License-Identifier: MIT
"""Compare counter factoring to135, including conflicting commands and reset."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_screen137 import ROOT,put,sha,factor_counter
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER','') in ['18000@localhost','18000@127.0.0.1']
 original=a.baseline/'nes-command135/evidence/fit03/nes_rom_loader.sv'
 meta=json.loads((a.baseline/'nes-command135/evidence/manifest.json').read_bytes())['files'];assert sha(original)==meta['fit03/nes_rom_loader.sv']
 s=original.read_text();put(o/'nes_rom_loader.sv',factor_counter(s));put(o/'reference.sv',s.replace('module nes_rom_loader #','module nes_rom_loader_reference #'))
 shutil.copy2(ROOT/'tests/nes-functional/loader128_diff_tb.sv',o/'loader128_diff_tb.sv')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_loader.sv','reference.sv','loader128_diff_tb.sv'],'compile')
 run('vsim',['-c','loader128_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'diff')
 log=(o/'diff.log').read_text();assert 'PASS128 DIFF one_step_cases=26112' in log and '** Fatal:' not in log
 s=factor_counter(s);needle='else if(count_advance)loaded_bytes<=loaded_bytes+1\'b1;';assert s.count(needle)==1
 put(o/'negative.sv',s.replace(needle,"else if(count_advance)loaded_bytes<=loaded_bytes+2'd2;"))
 run('vlog',['-sv','negative.sv'],'negative-compile');run('vsim',['-c','loader128_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative')
 assert '** Fatal: DIFF128' in (o/'negative.log').read_text()
 put(o/'result.json',json.dumps(dict(passed=True,one_step_cases=26112,wrong_increment_rejected=True,
   reference_sha256=sha(original),candidate_sha256=sha(o/'nes_rom_loader.sv')),indent=2)+'\n')
 print('PASS137 counter26112 cases and wrong-increment negative')
if __name__=='__main__':main()
