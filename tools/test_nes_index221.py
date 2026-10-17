# SPDX-License-Identifier: MIT
"""Actual selected220 allocator vs221 index; actual planner/reference regression."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_resident211 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 selected=BASE/'probes/nes-status220/arm01/src';manifest=json.loads((selected.parents[1]/'manifest01.json').read_bytes())
 pins={}
 for n in ['nes_resident211.c','nes_resident211.h','nes_planner211.c','nes_native165.c','nes_native165.h','nes_native_video165.h','nes_plan191.h','nes_trace166.c','nes_trace166.h']:
  src=selected/n;assert manifest['arm01/src/'+n]==sha(src);pins[str(src.relative_to(BASE))]=sha(src);shutil.copyfile(src,d/n)
 old=(d/'nes_resident211.c').read_text().replace('nes_resident211_','baseline_').replace('baseline_write_fn','nes_resident211_write_fn')
 old=old.replace('#include <string.h>','#include <string.h>\nextern unsigned long long baseline_probes;')
 for cond in ['i<stop&&i<live','i<stop&&i<occupied','i<stop']:
  old=old.replace(f'for(unsigned i=first;{cond};i++)if(',f'for(unsigned i=first;{cond};i++)if((++baseline_probes,1)&&')
 (d/'baseline.c').write_text(old,encoding='utf8',newline='\n')
 for n in ['c','h']:
  src=ROOT/f'src/nes/firmware/nes_resident221.{n}';pins[str(src.relative_to(BASE))]=sha(src);shutil.copyfile(src,d/f'nes_resident211.{n}')
 # Instrument remaining allocation fallback probes only in host evidence.
 f=d/'nes_resident211.c';s=f.read_text()
 for cond in ['i<stop&&i<occupied','i<stop']:
  s=s.replace(f'for(unsigned i=first;{cond};i++)if(',f'for(unsigned i=first;{cond};i++)if((PROBE221(),1)&&')
 f.write_text(s,encoding='utf8',newline='\n')
 src=ROOT/'tests/nes-functional/index221_host.c';shutil.copyfile(src,d/src.name);pins[str(src.relative_to(BASE))]=sha(src)
 prior=BASE/'probes/nes-resident211/test04'
 for n in ['resident211_host.c','scene203.inc','reference203.c','reference203.h']:
  shutil.copyfile(prior/n,d/n);pins[str((prior/n).relative_to(BASE))]=sha(prior/n)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (d/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(d/(name+'.log')).read_text(errors='replace');assert r.returncode==0,text[-6000:];return text
 flags=['-std=c11','-Wall','-Wextra','-Werror','-O2']
 run([gcc,*flags,'-DNES_INDEX221_PROFILE','index221_host.c','nes_resident211.c','baseline.c','-o','index.exe'],'build-index')
 index=run([d/'index.exe'],'index');assert 'PASS INDEX221' in index
 # Compile uninstrumented production candidate against existing real planner
 # and186 reference; no new geometry/consumer model substituted.
 shutil.copyfile(ROOT/'src/nes/firmware/nes_resident221.c',d/'nes_resident211.c')
 run([gcc,*flags,'resident211_host.c','nes_resident211.c','nes_planner211.c','nes_native165.c','nes_trace166.c','reference203.c','-o','reference.exe'],'build-reference')
 reference=run([d/'reference.exe'],'reference');assert 'PASS RESIDENT211' in reference
 result=dict(passed=True,index=index,reference=reference,inputs=pins,public_source_sha256=sha(Path(__file__)),
  scope='Actual selected220 C allocator exact slots/state/plan comparison; synthetic scrolling and collision pressure. Real selected planner vs186 reference. Not physical performance or full C/RTL/SNES join.',new_fit=False,physical=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(index+reference)
if __name__=='__main__':main()
