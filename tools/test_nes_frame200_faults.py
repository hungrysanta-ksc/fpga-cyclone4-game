# SPDX-License-Identifier: MIT
"""Pin-level SPI malformed input, descriptor snapshot and common STOP tests."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False);assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins={};files=[ROOT/'src/nes/rtl'/n for n in ('nes_plan_spi200.sv','nes_plan_batch200.sv')]
 files+=[BASE/'probes/nes-window184-coupled/evidence/route02'/n for n in ('nes_domain_reset124.sv','nes_native_mailbox165.sv')]
 files+=[ROOT/'tests/nes-functional'/n for n in ('spi200_bus.svh','frame200_faults_tb.sv')]
 for f in files:shutil.copyfile(f,a.out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 env=os.environ.copy();env['PATH']=str(a.questa_bin)+os.pathsep+env.get('PATH','')
 def run(name,args):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:];return text
 run('vlib',['work']);run('vlog',['-sv',*[f.name for f in files if f.suffix=='.sv']])
 text=run('vsim',['-c','work.frame200_faults_tb','-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000','-do','onerror {quit -code 1}; run -all; quit -f'])
 m=re.search(r'PASS BATCH200FAULT checks=(\d+)',text);assert m and int(m[1])==50
 result=dict(passed=True,checks=int(m[1]),source_pins=pins,script_sha256=sha(Path(__file__)))
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
