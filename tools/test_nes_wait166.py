# SPDX-License-Identifier: MIT
"""Reproduce165 wait policy under finite legal delays; not a physical diagnosis."""
from pathlib import Path
import argparse,json,subprocess,shutil,re,os
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
 files=['src/nes/diagnostic/nes_native_fill165.sv','src/nes/diagnostic/nes_native_export165.sv','tests/nes-functional/native_fill165_tb.sv','tests/nes-functional/native_wait166_tb.sv','tools/test_nes_wait166.py']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 p=a.out/'native_fill165_tb.sv';s=p.read_text().replace('.MAX_CYCLES(MODE==6?50:262144),.WAIT_CYCLES(32)', '.MAX_CYCLES(2097152),.WAIT_CYCLES(131072)')
 s=s.replace('MODE!=12','(MODE!=12 || ticks>=140000)').replace('MODE!=11','(MODE!=11 || ticks>=140000)').replace('#10000000;','#20000000;')
 p.write_text(s)
 (a.out/'required.hex').write_text('1\n'+'0\n'*8191);(a.out/'chr.hex').write_text('5a\n'*131072)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_native_fill165.sv','nes_native_export165.sv','native_fill165_tb.sv','native_wait166_tb.sv'],'vlog');cases=[]
 for mode in [0,11,12]:
  s=run('vsim',['-c','work.native_fill165_tb',f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT=fill{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'fill{mode}')
  m=re.search(r'PASS FILL165[^\r\n]+',s);assert m;cases.append(m[0])
 for gap in [100,10000]:
  s=run('vsim',['-c','work.native_wait166_tb',f'-gGAP={gap}','-do','onerror {quit -code 1}; run -all; quit -f'],f'export{gap}')
  m=re.search(r'PASS WAIT166[^\r\n]+',s);assert m;cases.append(m[0])
 result=dict(passed=True,cases=cases,public_sources={n:sha(ROOT/n) for n in files},scope='Unchanged165 RTL. Finite140000-cycle grant/consumer delay exceeds fill WAIT131072; paced10000-cycle record consumer exceeds export4194304 during geometry. Models, not observed board pacing or confirmed root cause.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
