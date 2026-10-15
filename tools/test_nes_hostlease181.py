# SPDX-License-Identifier: MIT
"""Actual SPI endpoint + SNES bus lifecycle; external CPU/master are models."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 m=json.loads((a.prepared/'preparation.json').read_bytes());files=['nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','sink-program.hex']
 for n in files:assert sha(a.prepared/n)==m['sources'][n],n;shutil.copy2(a.prepared/n,a.out/n)
 tb=ROOT/'tests/nes-functional/hostlease181_tb.sv';shutil.copy2(tb,a.out/tb.name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
 run('vlib',['work'],'vlib');run('vlog',['-sv',*files[:-1],tb.name],'compile')
 s=run('vsim',['-c','work.hostlease181_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulate')
 match=re.search(r'PASS HOSTLEASE181 phases=16 commits=(\d+) cancels=(\d+) checks=(\d+)',s);assert match
 result=dict(passed=True,phases=16,commits=int(match[1]),cancels=int(match[2]),checks=int(match[3]),
  sources={n:sha(a.out/n) for n in files+[tb.name]},runner_sha256=sha(Path(__file__)),scope=__doc__,hardware=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(match[0],flush=True)
if __name__=='__main__':main()
