# SPDX-License-Identifier: MIT
"""Replay actual SPI/boot/reader with the combined counter and loader candidate."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from test_nes_retirece165 import connected

def main():
 p=argparse.ArgumentParser()
 for n in ['reference','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir()
 names=['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']
 for n in names:(a.out/n).write_bytes((a.prepared/n).read_bytes())
 (a.out/'reference.sv').write_text((a.reference/'nes_rom_spi.sv').read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1))
 (a.out/'tag165_tb.sv').write_text(connected())
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib')
 run('vlog',['-sv',*names,'reference.sv','tag165_tb.sv'],'compile')
 log=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'connected')
 summary=re.search(r'PASS TAG165[^\r\n]+',log)[0]
 assert 'edges=1026691 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in summary
 r=dict(passed=True,summary=summary,sources={n:sha(a.out/n) for n in names},reference_sha256=sha(a.reference/'nes_rom_spi.sv'),bench_sha256=sha(a.out/'tag165_tb.sv'),scope='Both candidate modules active in actual SPI/boot/READ16 composition; seeded loader READY/count, not full ROM/game/MCU.',public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_retirejoint165.py','tools/test_nes_retirece165.py','tools/test_nes_balancedlength165.py','tools/test_nes_stopclear165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
