# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins={}
 for n in ('src/nes/rtl/nes_tile191.sv','tests/nes-functional/tile191_faults_tb.sv'):
  shutil.copyfile(ROOT/n,a.out/Path(n).name);pins[n]=sha(ROOT/n)
 for tool,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_tile191.sv','tile191_faults_tb.sv'],'vlog'),
  ('vsim',['-c','work.tile191_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'fault')]:
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
 assert 'PASS TILE191FAULT cases=9' in s
 result=dict(passed=True,cases=9,pins=pins,scope='Local request/response lease/error/timeout/STOP-flush; not physical arbiter/CDC')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
