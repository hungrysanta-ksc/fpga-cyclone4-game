# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,subprocess,shutil,re,os
from nes_game147 import ROOT,sha
from nes_pacing167 import fill,exporter
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--reuse',type=Path);a=p.parse_args()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost' and str(a.out).isascii();a.out.mkdir(parents=True,exist_ok=False)
 files=['src/nes/diagnostic/nes_native_fill165.sv','src/nes/diagnostic/nes_native_export165.sv','src/nes/diagnostic/nes_native_arbiter165.sv','tests/nes-functional/native_pacing167_tb.sv','tests/nes-functional/native_fill165_tb.sv','tools/nes_pacing167.py','tools/test_nes_pacing167.py']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 for name,fn in [('nes_native_fill165.sv',fill),('nes_native_export165.sv',exporter)]:
  f=a.out/name;f.write_text(fn(f.read_text()),encoding='utf8',newline='\n')
 (a.out/'required.hex').write_text('1\n1\n'+'0\n'*8190);(a.out/'chr.hex').write_text('5a\n'*131072)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
 # Default-off compatibility plus cooperative cancellation/response regressions.
 base=(a.out/'native_fill165_tb.sv').read_text()
 (a.out/'cooperative_tb.sv').write_text(base.replace('native_fill165_tb','cooperative_tb').replace('.MAX_TILES(','.COOPERATIVE_WAIT(1),.MAX_TILES('),encoding='utf8',newline='\n')
 finite=base.replace('native_fill165_tb','finite_tb').replace('.MAX_CYCLES(MODE==6?50:262144),.WAIT_CYCLES(32)', '.COOPERATIVE_WAIT(1),.MAX_CYCLES(2097152),.WAIT_CYCLES(131072)')
 finite=finite.replace('MODE!=12','(MODE!=12 || ticks>=140000)').replace('MODE!=11','(MODE!=11 || ticks>=140000)').replace('MODE==0 || MODE==8','MODE==0 || MODE==11 || MODE==12 || MODE==8')
 (a.out/'finite_tb.sv').write_text(finite,encoding='utf8',newline='\n')
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_native_fill165.sv','nes_native_export165.sv','nes_native_arbiter165.sv','native_pacing167_tb.sv','native_fill165_tb.sv','cooperative_tb.sv','finite_tb.sv'],'vlog');results=[]
 cases=[dict(POLICY=p,GAP=g,PHASE=h,MODE=0) for p,g,h in [(0,1900,0),(1,1900,0),(2,1900,0),(2,1900,100000),(2,1900,200000),(0,20,301000),(2,20,301000)]]
 cases += [dict(POLICY=2,GAP=1900,MODE=m) for m in [1,2,3,4]]
 cases += [dict(POLICY=2,GAP=1900,MODE=0,TILES=32)]
 for i,c in enumerate(cases):
  if a.reuse and i<7:
   for n in ['nes_native_fill165.sv','nes_native_export165.sv','nes_native_arbiter165.sv','native_pacing167_tb.sv']:assert sha(a.out/n)==sha(a.reuse/n),n
   f=a.reuse/f'pacing{i:02}.log';s=f.read_text();assert 'Errors: 0' in s and all(f'-g{k}={v}' in s for k,v in c.items())
   shutil.copy2(f,a.out/f'pacing{i:02}.log')
  else:s=run('vsim',['-c','work.native_pacing167_tb',*[f'-g{k}={v}' for k,v in c.items()],'-do','onerror {quit -code 1}; run -all; quit -f'],f'pacing{i:02}')
  m=re.search(r'PASS PACING167[^\r\n]+',s);assert m;results.append(dict(parameters=c,result=m[0]))
 for mode in range(16):
  s=run('vsim',['-c','work.native_fill165_tb',f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT=fill{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'fill{mode}')
  assert 'PASS FILL165' in s
 for top,modes in [('cooperative_tb',[0,1,2,3,4,5,6,7,8,9,10,13,14,15]),('finite_tb',[11,12])]:
  for mode in modes:
   s=run('vsim',['-c','work.'+top,f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT={top}{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'{top}{mode}')
   assert 'PASS FILL165' in s
 result=dict(passed=True,cases=results,legacy_regression_modes=16,cooperative_regression_modes=14,finite_long_wait_modes=2,reused_pacing_cases=7 if a.reuse else 0,executed_copies={Path(n).name:sha(a.out/Path(n).name) for n in files},scope='Actual fill/arbiter/export; modeled1472 geometry records, NTSC slot duty, paced host, deterministic ROM bytes. No new core boot or physical pacing claim. Copied RTL hashes include generated transformations; source copies identify the executed tool revision.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
