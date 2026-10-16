# SPDX-License-Identifier: MIT
"""205 stream into actual193 RAM: partial tile fault isolation and stable backpressure."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins={};names=[]
 for f in [ROOT/'src/nes/rtl/nes_tile205.sv',ROOT/'src/nes/rtl/nes_tile_bulk193.sv',ROOT/'src/nes/rtl/nes_bulk_aperture188.sv',BASE/'probes/nes-board204/source01/nes_native_mailbox165.sv',BASE/'probes/nes-board204/source01/nes_domain_reset124.sv',ROOT/'tests/nes-functional/tile_stream205_tb.sv']:
  shutil.copyfile(f,a.out/f.name);names.append(f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 for tool,args in [('vlib',['work']),('vlog',['-sv',*names]),('vsim',['-c','work.tile_stream205_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(tool+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 m=re.search(r'PASS STREAM205 checks=(\d+)',t);assert m
 result=dict(passed=True,checks=int(m[1]),source_pins=pins,script_sha256=sha(Path(__file__)),scope=__doc__,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])
if __name__=='__main__':main()
