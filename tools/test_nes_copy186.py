# SPDX-License-Identifier: MIT
"""Differential converter and exact map packet reconstruction. Mock ACKs only."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['out','candidate','prior','gcc']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--maps',nargs='*',type=Path,default=[])
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 pins={}
 for f in a.candidate.glob('nes_*'):
  if f.is_file():shutil.copyfile(f,a.out/f.name);pins[f.name]=sha(f)
 src=a.prior/'nes_native_video165.c'
 (a.out/'legacy.c').write_text(src.read_text().replace('nes_native_video165_build(', 'legacy_build('),encoding='utf8');pins['legacy.c']=sha(src)
 host=ROOT/'tests/nes-functional/copy186_host.c';shutil.copyfile(host,a.out/'host.c');pins['host.c']=sha(host)
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 def run(cmd,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,s;return s
 run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','host.c','legacy.c','nes_native_video165.c','nes_native_sink165.c','nes_native165.c','nes_trace166.c','nes_sink_trace168.c','-o','host.exe'],'gcc')
 maps=[f.resolve() for f in a.maps]
 for i,f in enumerate(maps):pins['map_input'+str(i)]=sha(f);shutil.copyfile(f,a.out/('map_input'+str(i)+'.bin'))
 result=run([a.out/'host.exe',*maps],'host');print(result,flush=True)
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,result=result,pins=pins,scope=__doc__),indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
