# SPDX-License-Identifier: MIT
"""Only changed first-fault observer; no repeated whole-game/core regression."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True)
 for src in [a.prepared/'nes_run_observer134.sv',ROOT/'tests/nes-functional/game154_observer_tb.sv']:shutil.copy2(src,a.out/src.name)
 for exe,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_run_observer134.sv','game154_observer_tb.sv'],'vlog'),('vsim',['-c','work.game154_observer_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')]:
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  log=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',log),log[-2400:]
 assert 'PASS154 observer' in log
 result=dict(passed=True,observer_sha256=sha(a.out/'nes_run_observer134.sv'),test_sha256=sha(a.out/'game154_observer_tb.sv'),result=re.search(r'PASS154[^\r\n]+',log)[0],physical=False,scope='Synthetic fault edge and PPU state, exact new SPI observer. Not actual153 root cause.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
