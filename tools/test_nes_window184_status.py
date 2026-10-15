# SPDX-License-Identifier: MIT
"""New diagnostic fields tested against unchanged RTL traces and injected failures."""
from pathlib import Path
import argparse,json,os,subprocess,shutil
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['traces','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 sources=['src/nes/firmware/nes_sink_window184.c','src/nes/firmware/nes_sink_window184.h','tests/nes-functional/sink_window184_host.c']
 for n in sources:shutil.copyfile(ROOT/n,a.out/Path(n).name)
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,label):
  with (a.out/(label+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert q.returncode==0,s;return s
 run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','sink_window184_host.c','nes_sink_window184.c','-o','host.exe'],'gcc')
 cases=[]
 for name in ['normal','phase','wrap']:
  t=(a.traces/name/'transactions.txt').resolve();s=run([(a.out/'host.exe').resolve(),t,int(name=='wrap')],name)
  assert 'failures=107' in s;cases.append(dict(name=name,output=s,trace_sha256=sha(t)))
 result=dict(passed=True,cases=cases,public_sources={n:sha(ROOT/n) for n in sources+['tools/test_nes_window184_status.py']},scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
