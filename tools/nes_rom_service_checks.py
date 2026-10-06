# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,sys
from nes_ncr1_live import ROOT,put,sha
def main():
 sys.argv.pop(1);p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--delay',type=int,default=1);a=p.parse_args()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 for n in ('src/nes/nes_rom_service.sv','tests/nes-functional/rom_service_tb.sv'):shutil.copy2(ROOT/n,out/Path(n).name)
 sources={p.name:sha(p) for p in out.iterdir()}
 for tool,args,name in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_rom_service.sv','rom_service_tb.sv'],'vlog'),('vsim',['-c','rom_service_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')]:
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,name
 log=(out/'simulation.log').read_text();m=re.search(r'PASS ROM SERVICE checks=(\d+) requests=(\d+) cache_pairs=256 negative_cases=6',log)
 assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect raw simulation.log'
 result=dict(candidate='NES-R1-ROM-SERVICE-050',passed=True,checks=int(m[1]),requests=int(m[2]),cache_pairs=256,negative_cases=6,sources=sources)
 put(out/'result.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
