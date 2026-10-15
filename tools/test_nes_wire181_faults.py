# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True)
 sources={}
 for n in ('src/nes/video/nes_native_export181.sv','tests/nes-functional/wire181_faults_tb.sv'):
  shutil.copy2(ROOT/n,a.out/Path(n).name);sources[n]=sha(ROOT/n)
 for exe,args in [('vlib',['work']),('vlog',['-sv','nes_native_export181.sv','wire181_faults_tb.sv']),('vsim',['-c','work.wire181_faults_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(exe+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60)
  s=(a.out/(exe+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
 assert 'PASS WIRE181FAULT cases=7' in s
 result=dict(passed=True,cases=7,sources=sources,runner_sha256=sha(Path(__file__)),scope='Raw phase backpressure, query miss, invalid color, lease loss, disable, stalled deadline, reset. Stub fill; no SPI or physical timing.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print('PASS WIRE181FAULT cases=7')
if __name__=='__main__':main()
