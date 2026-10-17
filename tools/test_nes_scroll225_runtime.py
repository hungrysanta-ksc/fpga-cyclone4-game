# SPDX-License-Identifier: MIT
"""Actual225 RUN/queue/retire with decoded-geometry-equivalent2231 fixtures.
Only BEGIN version changes on archived scalar ingress; no packed wire proof
claimed here. Exporter223 wire proof is reused unchanged.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_scroll225 import ROOT,BASE,sha
from test_nes_scroll225 import host_source

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-index221/runtime01';pins={}
 for n in ['host213.c','reference203.c','reference203.h']+[f'scene{i}.wire' for i in range(11)]:
  f=old/n;shutil.copyfile(f,d/n);pins[str(f.relative_to(BASE))]=sha(f)
 for f in (a.arm/'src').iterdir():
  if f.name.startswith('nes_') and f.suffix in ['.c','.h','.inc']:shutil.copyfile(f,d/f.name)
 for i in range(11):
  f=d/f'scene{i}.wire';lines=f.read_text().splitlines();assert lines[0][8:12]=='2031'
  lines[0]=lines[0][:8]+'2231'+lines[0][12:];f.write_text('\n'.join(lines)+'\n',encoding='ascii')
 h=(d/'host213.c').read_text();v=host_source();v=v[v.index('static void verify_bank(void){'):v.index('static void run_frame(')]
 start=v.index(' for(unsigned g=0;g<64;g++)');end=v.index(' assert(!memcmp(banks[bank].map',start);v=v[:start]+v[end:]
 v=v.replace('candidate','output').replace('refbg','bg').replace('refobj','obj').replace('word(', 'u16(')
 start=h.index('static void verify_bank(void){');end=h.index('static void init(void){',start);h=h[:start]+v+h[end:]
 (d/'host213.c').write_text(h,encoding='utf8',newline='\n')
 files=['host213.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_budget210.c']
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 for args,name in [([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],'build'),([d/'host.exe'],'run')]:
  with (d/(name+'.log')).open('wb') as log:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0,text[-6000:]
 assert 'frames=9 ' in text and text.count('PASS METADATA203 fault=')==6
 result=dict(passed=True,output=text,inputs=pins,source_hashes={n:sha(d/n) for n in files},scope=__doc__,physical=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(text)
if __name__=='__main__':main()
