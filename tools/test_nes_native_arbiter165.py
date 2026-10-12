# SPDX-License-Identifier: MIT
"""Unchanged READ16 reader phase/priority/drain tests for the fill adapter."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha,VHDL,SV,EXTRA
from nes_native_memory165 import prepare,FILES
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 manifest=a.evidence/'manifest.json';assert sha(manifest)==json.loads((ROOT/'analysis/game164-verification.json').read_bytes())['manifest_sha256']
 pin=json.loads(manifest.read_bytes())['files']['asm/nes_rom_physical.sv'];reader=a.evidence/'asm/nes_rom_physical.sv';assert sha(reader)==pin
 prepare(a.evidence,a.out)
 assert sha(a.out/'nes_rom_physical.sv')==pin
 files=['src/nes/diagnostic/nes_native_arbiter165.sv','tests/nes-functional/native_arbiter165_tb.sv']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*FILES,'nes_native_ciram165.sv',Path(files[1]).name],'vlog');cases=[]
 for i,phase in enumerate([0,.75,1.5,2.25,3,3.75,4.5,5.25]):
  s=run('vsim',['-c','work.native_arbiter165_tb',f'-gPHASE={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],f'phase-{i}')
  m=re.search(r'PASS ARBITER165 phase=([\d.]+) checks=(\d+) reads=(\d+) max=(\d+)',s);assert m
  cases.append(dict(phase_ns=phase,checks=int(m[2]),reads=int(m[3]),maximum_nes_edges=int(m[4])))
 result=dict(passed=True,cases=cases,reader_sha256=pin,generated_joint_sha256=sha(a.out/'nes_live_joint.sv'),parent_joint_compiled_only=True,public_sources={n:sha(ROOT/n) for n in files+['tools/test_nes_native_arbiter165.py']},
  scope='Synthetic admission predicates; actual unchanged physical reader with70ns memory and8 clock phases. Core slot qualification separately tested by actual-core run. No analog MTBF, board IO, host CDC or first-level proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
