# SPDX-License-Identifier: MIT
"""Rebind the established real SPI/boot/reader test to the flattened loader."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_board204 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert str(a.out).isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-boundary218';prior=json.loads((d/'test01/result.json').read_bytes())
 for n in ['reference.sv','candidate.sv','connected_tb.sv']:
  assert sha(d/'test01'/n)==prior['sources'][n];(a.out/n).write_bytes((d/'test01'/n).read_bytes())
 assert (a.out/'candidate.sv').read_text()==(d/'source02/nes_rom_spi.sv').read_text()
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((d/'source02'/n).read_bytes())
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  t=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-3000:];return t
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','connected_tb.sv'],'compile')
 t=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'connected')
 assert 'wire_bits=14016' in t and 'acks=7 corruptions=19 cancels=72 overlaps=2' in t
 r=dict(passed=True,summary=re.search(r'PASS TAG165[^\r\n]+',t)[0],sources={x.name:sha(x) for x in a.out.glob('*.sv')},script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
