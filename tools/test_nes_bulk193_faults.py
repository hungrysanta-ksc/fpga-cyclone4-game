# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02';names=[];pins={}
 for src in [board/'nes_domain_reset124.sv',board/'nes_native_mailbox165.sv',ROOT/'src/nes/rtl/nes_bulk_aperture188.sv',
             ROOT/'src/nes/rtl/nes_tile_bulk193.sv',ROOT/'tests/nes-functional/tile_bulk193_faults_tb.sv']:
  shutil.copyfile(src,a.out/src.name);names.append(src.name);pins[src.relative_to(ROOT.parent).as_posix()]=sha(src)
 for tool,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv',*names],'vlog'),
  ('vsim',['-c','work.tile_bulk193_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'fault')]:
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
 assert 'PASS BULK193FAULT cases=8' in s
 result=dict(passed=True,cases=8,source_pins=pins,scope='Malformed tile/frame, partial STOP, stopped-host STOP, source fault, token exhaustion; not exhaustive CDC phases')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(passed=True,cases=8)))
if __name__=='__main__':main()
