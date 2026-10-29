# SPDX-License-Identifier: MIT
import argparse,shutil,subprocess,json
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
for f in a.arm.glob('*.h'):shutil.copyfile(f,d/f.name)
for n in ['nes_native165.c','nes_trace166.c','nes_cost471.c','nes_budget210.c']:shutil.copyfile(a.arm/n,d/n)
for n in ['guards.c','cost_format.c']:shutil.copyfile(ROOT/'tests/nes-nrom471'/n,d/n)
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name,sources,flags in [('guards',['guards.c','nes_native165.c','nes_trace166.c'],[]),('format',['cost_format.c','nes_cost471.c','nes_budget210.c'],['-DNES_COST471_HOST'])]:
 for label,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,*sources,'-o',name+'.exe']),('test',[str(d/(name+'.exe'))])]:
  with(d/(name+'-'+label+'.log')).open('wb') as f:r=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT)
  assert r.returncode==0,(d/(name+'-'+label+'.log')).read_text(errors='replace')[-2000:]
r={'passed':True,'receiver':sha(a.arm/'nes_native165.c'),'cost':sha(a.arm/'nes_cost471.c'),'guards':(d/'guards-test.log').read_text().strip(),'format':(d/'format-test.log').read_text().strip()};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
