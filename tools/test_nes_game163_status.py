# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True)
 shutil.copy2(a.prepared/'nes_screen_status151.sv',a.out/'nes_screen_status151.sv');shutil.copy2(ROOT/'tests/nes-functional/game163_status_tb.sv',a.out/'game163_status_tb.sv')
 for name,args in [('vlib',['work']),('vlog',['-sv','nes_screen_status151.sv','game163_status_tb.sv']),('vsim',['-c','work.game163_status_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-2000:]
 assert 'PASS163 STATUS54' in s
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,cases=54,rtl_sha256=sha(a.out/'nes_screen_status151.sv'),test_sha256=sha(a.out/'game163_status_tb.sv'),scope='Unchanged162 status RTL: A9/E1-E5 late-write capture, SPI, STOP retention and reset; modeled pins, not physical bus measurement.'),indent=2)+'\n');print('PASS163 status54')
if __name__=='__main__':main()
