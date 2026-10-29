# SPDX-License-Identifier: MIT
"""Use production 227 C plan service to serialize verified 430 plans."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--planner',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
r=json.loads((a.planner/'result.json').read_text());assert r['passed'] and r['plans_sha256']==sha(a.planner/'plans.bin');src=BASE/'probes/nes-repeat227/arm01/src'
for f in src.glob('*.h'):shutil.copyfile(f,d/f.name)
shutil.copyfile(src/'nes_plan_service200.c',d/'nes_plan_service200.c');shutil.copyfile(ROOT/'tests/nes-nrom430/serialize.c',d/'serialize.c');shutil.copyfile(a.planner/'plans.bin',d/'plans.bin')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','serialize.c','-o','host.exe']),('test',[str(d/'host.exe'),'plans.bin','batch.bin'])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-2000:]
assert 'PASS actual 227 plan service' in (d/'test.log').read_text();raw=(d/'batch.bin').read_bytes();assert len(raw)==21 and raw[0]==0xe9
result={'passed':True,'plan_sha256':sha(a.planner/'plans.bin'),'batch_sha256':sha(d/'batch.bin'),'service_sha256':sha(src/'nes_plan_service200.c'),'scope':'actual 227 plan service with modeled E8 responses, no RTL or real ARM timing'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
