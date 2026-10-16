# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src=BASE/'probes/nes-board206/source03';prep=json.loads((src/'preparation206.json').read_bytes());pins={};names=[]
 for n in ['nes_tile_bulk206.sv','nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv','nes_bulk_aperture188.sv']:
  f=src/n;assert sha(f)==prep['sources'][n];shutil.copyfile(f,a.out/n);names.append(n);pins[f.relative_to(BASE).as_posix()]=sha(f)
 f=ROOT/'tests/nes-functional/cancel206_tb.sv';shutil.copyfile(f,a.out/f.name);names.append(f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 for tool,args in [('vlib',['work']),('vlog',['-sv',*names]),('vsim',['-c','work.cancel206_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(tool+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 assert 'PASS CANCEL206 checks=21' in t
 result=dict(passed=True,checks=21,external_cancel_cases=18,local_fault_cases=2,recovery=1,source_pins=pins,script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print('PASS CANCEL206 checks=21')
if __name__=='__main__':main()
