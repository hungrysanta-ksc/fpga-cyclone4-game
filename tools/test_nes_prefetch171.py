# SPDX-License-Identifier: MIT
"""Actual FIFO fill/arbiter/export; modeled slot/host pacing, no physical claim."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 for n in ['nes_native_fill165.sv','nes_native_export165.sv','nes_native_arbiter165.sv']:shutil.copyfile(a.candidate/n,a.out/n)
 (a.out/'old_fill.sv').write_text((a.baseline/'nes_native_fill165.sv').read_text().replace('module nes_native_fill165','module old_fill'),encoding='utf-8')
 base=(ROOT/'tests/nes-functional/native_pacing167_tb.sv').read_text()
 # Identical public query/slot/core-traffic/host schedules for each comparison.
 base=base.replace('module native_pacing167_tb;','module prefetch171_tb;').replace('parameter POLICY=2,','parameter BUFFERED=1, POLICY=2,')
 base=base.replace('nes_native_fill165 #(', 'FILL_MODULE #(')
 for old,new in [('native_pacing167_tb','prefetch171_tb'),('PASS PACING167','PASS PREFETCH171')]:base=base.replace(old,new)
 base=base.replace('(POLICY==2 || GAP==20)','((POLICY==2 && (BUFFERED || TILES<=32)) || GAP==20)')
 base=base.replace('if(MODE==0 && POLICY==1', 'if(MODE==0 && !BUFFERED && TILES>32 && (ee!=4||exp.fill_detail!=3))$fatal(1,"baseline total limit");\n    if(MODE==0 && POLICY==1')
 base=base.replace('initial begin #400000000;', 'initial begin #700000000;')
 for name,mod in [('prefetch171_tb','nes_native_fill165'),('baseline171_tb','old_fill')]:
  (a.out/(name+'.sv')).write_text(base.replace('prefetch171_tb',name).replace('FILL_MODULE',mod),encoding='utf-8')
 shutil.copyfile(ROOT/'tests/nes-functional/native_fill165_tb.sv',a.out/'native_fill165_tb.sv')
 (a.out/'required.hex').write_text('1\n2\n3\n'+'0\n'*8189)
 (a.out/'chr.hex').write_text(''.join(f'{(i*37+i//256)&255:02x}\n' for i in range(131072)))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=360)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_native_fill165.sv','nes_native_export165.sv','nes_native_arbiter165.sv','old_fill.sv','native_fill165_tb.sv','prefetch171_tb.sv','baseline171_tb.sv'],'vlog')
 results=[]
 for mode in range(16):
  s=run('vsim',['-c','work.native_fill165_tb',f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT=fill{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'fill{mode}')
  assert 'PASS FILL165' in s;results.append(re.search(r'PASS FILL165[^\r\n]+',s)[0])
 for i,(buffered,tiles,gap,phase,mode) in enumerate([(0,128,1900,0,0),(1,128,1900,0,0),(1,512,1900,0,0),(1,512,1900,200000,0),(1,128,500,0,0),(1,15,1900,0,1),(1,15,1900,0,2),(1,15,1900,0,3),(1,15,1900,0,4)]):
  top='prefetch171_tb' if buffered else 'baseline171_tb'
  s=run('vsim',['-c','work.'+top,f'-gBUFFERED={buffered}',f'-gTILES={tiles}',f'-gGAP={gap}',f'-gPHASE={phase}',f'-gMODE={mode}','-do','onerror {quit -code 1}; run -all; quit -f'],f'pacing{i:02}')
  assert 'PASS PREFETCH171' in s;results.append(re.search(r'PASS PREFETCH171[^\r\n]+',s)[0]);print(results[-1],flush=True)
 r=dict(passed=True,results=results,source_sha256=sha(a.candidate/'nes_native_fill165.sv'),executed_sources={p.name:sha(p) for p in a.out.glob('*.sv')},public_sources={n:sha(ROOT/n) for n in ['tools/nes_prefetch171.py','tools/test_nes_prefetch171.py','tests/nes-functional/native_pacing167_tb.sv','tests/nes-functional/native_fill165_tb.sv']},scope='Actual fill/arbiter/export with modeled query, ROM, qualified slots and host. No measured hardware wait breakdown, no whole-game/FPS claim.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS171 all functional cases')
if __name__=='__main__':main()
