# SPDX-License-Identifier: MIT
"""Existing167 wire SPI/boot/READ16 replay with the174 lookahead loader.

READY/count are seeded to avoid full-ROM writes. Not a game or board test.
"""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from test_nes_rawstage167 import connected

def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 names=['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']
 for n in names:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 s=(a.candidate/'nes_rom_spi.sv').read_text()
 (a.out/'reference.sv').write_text(s.replace('module nes_rom_spi_check(','module baseline_check165(',1))
 s=connected();needle="boot.loader.phase=16'h10;";assert s.count(needle)==1
 s=s.replace(needle,needle+"boot.loader.reject_state=4'b1100;")
 (a.out/'connected.sv').write_text(s)
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:]);return log
 run('vlib',['work'],'vlib');run('vlog',['-sv',*names,'reference.sv','connected.sv'],'compile')
 log=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'connected')
 assert 'wire_bits=14016' in log and 'acks=7 corruptions=19 cancels=72 overlaps=2' in log
 r=dict(passed=True,summary=re.search(r'PASS TAG165[^\r\n]+',log)[0],wire_bits=14016,scope=__doc__,sources={n:sha(a.out/n) for n in [*names,'reference.sv','connected.sv']},public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_legality174_spi.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['summary'])
if __name__=='__main__':main()
