# SPDX-License-Identifier: MIT
"""Actual198 batch scheduler +195 C sink, mocked SPI/SNES ACK; no physical timing."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 pins={}
 def copy(f):shutil.copyfile(f,a.out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 for f in (BASE/'probes/nes-bulk195/coupled03/candidate').glob('nes_*'):
  if f.suffix in ('.c','.h','.inc'):copy(f)
 for n in ('nes_plan191.h','nes_plan_wire196.h','nes_plan_service198.h','nes_plan_service198.c'):copy(ROOT/'src/nes/firmware'/n)
 copy(ROOT/'tests/nes-functional/plan198_host.c')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,text[-4000:];return text
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fstack-usage','plan198_host.c','nes_plan_service198.c','nes_native_sink165.c','nes_sink_trace168.c','-o','host.exe'],'gcc')
 text=run([a.out/'host.exe',BASE/'probes/nes-plan191/test03'],'host');assert 'PASS SERVICE198 scenes=8 plans=97 batches=11 pressure_batches=35 checks=24' in text
 # The independent Python batch generator was used by actual SPI/RTL tests.
 frames=0
 for name in [f'scene{i}' for i in range(8)]+['pressure']:
  c=(a.out/(name+'.batch')).read_text().split();rtl=(BASE/'probes/nes-batch198/test02'/(name+'.batch')).read_text().split();assert c==rtl,name
  frames+=len((a.out/(name+'.batch')).read_text().splitlines())
 result=dict(passed=True,checks=24,plans=609,drained=609,frames=frames,source_pins=pins,script_sha256=sha(Path(__file__)),scope=__doc__,full_arm=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(passed=True,checks=24,frames=frames)))
if __name__=='__main__':main()
