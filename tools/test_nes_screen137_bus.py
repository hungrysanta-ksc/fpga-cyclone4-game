# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_screen137 import ROOT,put,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER','') in ['18000@localhost','18000@127.0.0.1']
 for n in ['nes_screen_bus137.sv','screen-program.hex']:shutil.copy2(a.candidate/n,o/n)
 shutil.copy2(ROOT/'tests/nes-functional/screen137_bus_tb.sv',o/'screen137_bus_tb.sv')
 put(o/'screen-full.hex',''.join(f'{x:02x}\n' for x in (a.candidate/'client/screen137.sfc').read_bytes()))
 for tool,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_screen_bus137.sv','screen137_bus_tb.sv'],'compile'),('vsim',['-c','screen137_bus_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'bus')]:
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 log=(o/'bus.log').read_text();assert 'PASS137 BUS rom_bytes=65536' in log and '** Fatal:' not in log
 put(o/'result.json',json.dumps(dict(passed=True,rom_bytes=65536,rom_sha256=sha(a.candidate/'client/screen137.sfc'),
   program_sha256=sha(o/'screen-program.hex'),boundary_sha256=sha(o/'nes_screen_bus137.sv')),indent=2)+'\n')
 print('PASS137 bus64KiB LoROM mapping and STOP/reset isolation')
if __name__=='__main__':main()
