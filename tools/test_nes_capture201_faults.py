# SPDX-License-Identifier: MIT
"""Source lifetime fault/STOP tests; no game or performance claim."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from test_nes_capture201 import ROOT,BASE,sha
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 files=[ROOT/'src/nes/rtl/nes_capture_lease201.sv',ROOT/'tests/nes-functional/capture201_faults_tb.sv']
 pins={f.relative_to(BASE).as_posix():sha(f) for f in files}
 for f in files:shutil.copyfile(f,a.out/f.name)
 env=os.environ.copy();env['PATH']=str(a.questa_bin)+os.pathsep+env.get('PATH','')
 for name,args in [('vlib',['work']),('vlog',['-sv',*[f.name for f in files]]),
  ('vsim',['-c','work.capture201_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(name+'.log')).open('wb') as log:
   r=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-4000:]
 m=re.search(r'PASS CAPTURE201FAULT checks=(\d+)',t);assert m and int(m[1])==23
 result=dict(passed=True,checks=int(m[1]),source_pins=pins,script_sha256=sha(Path(__file__)))
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])
if __name__=='__main__':main()
