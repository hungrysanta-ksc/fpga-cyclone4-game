# SPDX-License-Identifier: MIT
"""Actual service reply/fill boundaries, paired old160 causal control."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';assert not a.out.exists();a.out.mkdir(parents=True)
 old=a.baseline/'nes-game160/evidence/asm/nes_rom_service.sv'
 pins=json.loads((a.baseline/'nes-game160/evidence/manifest.json').read_bytes())['files'];assert sha(old)==pins['asm/nes_rom_service.sv']
 results={}
 for name,src,control in [('old',old,1),('new',a.prepared/'nes_rom_service.sv',0)]:
  d=a.out/name;d.mkdir();shutil.copy2(src,d/'nes_rom_service.sv');shutil.copy2(ROOT/'tests/nes-functional/game161_cache_tb.sv',d/'game161_cache_tb.sv')
  for exe,args in [('vlib',['work']),('vlog',['-sv','nes_rom_service.sv','game161_cache_tb.sv']),('vsim',['-c','work.game161_cache_tb',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'])]:
   with (d/(exe+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=90)
   s=(d/(exe+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
  assert 'PASS161 '+name.upper() in s
  results[name]=dict(source_sha256=sha(src),result=re.search(r'PASS161[^\r\n]+',s)[0],log_sha256=sha(d/'vsim.log'))
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,results=results,test_sha256=sha(ROOT/'tests/nes-functional/game161_cache_tb.sv'),scope='Actual service; legal request/reply seeded cache, response timing driven. Not full PPU/game replay or hardware proof.'),indent=2)+'\n');print(results)
if __name__=='__main__':main()
