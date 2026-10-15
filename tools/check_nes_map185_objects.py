# SPDX-License-Identifier: MIT
"""Compare ARM object/layout deltas; NOT a linked RUN/IRQ stack approval."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import sha

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','candidate','out','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);results={}
 env=os.environ.copy();env['PATH']=str(a.arm_bin)+os.pathsep+env.get('PATH','')
 for name,src in [('prior',a.prior),('candidate',a.candidate)]:
  d=a.out/name;d.mkdir();pins={}
  for f in src.glob('nes_*'):
   if f.is_file() and f.suffix in ['.c','.h']:shutil.copyfile(f,d/f.name);pins[f.name]=sha(f)
  (d/'layout.c').write_text('#include "nes_native_runtime165.h"\nchar video_size[sizeof(struct nes_native_video165)];\nchar sink_size[sizeof(struct nes_native_sink165)];\n',encoding='utf8')
  def run(tool,args,log):
   with (d/(log+'.log')).open('wb') as f:r=subprocess.run([str(a.arm_bin/('arm-none-eabi-'+tool+'.exe')),*args],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
   s=(d/(log+'.log')).read_text(errors='replace');assert r.returncode==0,s;return s
  names=['nes_native_video165','nes_native_sink165','nes_native_runtime165','nes_sink_window184']
  run('gcc',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c',*[n+'.c' for n in names],'layout.c'],'compile')
  nm=run('nm',['-S','layout.o'],'layout');run('size',[n+'.o' for n in names],'sizes')
  run('objdump',['-dr',*[n+'.o' for n in names]],'disassembly')
  stacks={}
  for f in d.glob('*.su'):
   for line in f.read_text().splitlines():
    loc,count,kind=line.split('\t');stacks[loc.rsplit(':',1)[-1]]=dict(bytes=int(count),kind=kind)
  results[name]=dict(layout={n:int(re.search(r'\w+\s+([\da-f]+)\s+\w\s+'+n,nm)[1],16) for n in ['video_size','sink_size']},stacks=stacks,input_pins=pins)
 result=dict(passed=True,results=results,scope=__doc__,full_runtime_approved=False,script_sha256=sha(Path(__file__)))
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({n:dict(layout=v['layout'],stacks={k:s for k,s in v['stacks'].items() if 'build' in k or 'map185' in k or 'seal' in k or 'step' in k}) for n,v in results.items()}))
if __name__=='__main__':main()
