# SPDX-License-Identifier: MIT
"""Check143 MIF-only program/atlas mapping with unchanged142 bus RTL."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 for n in ['nes_screen_bus137.sv','screen-program.hex']:shutil.copy2(a.candidate/n,o/n)
 shutil.copy2(ROOT/'tests/nes-functional/screen137_bus_tb.sv',o/'screen137_bus_tb.sv')
 (o/'screen-full.hex').write_text(''.join(f'{v:02x}\n' for v in (a.candidate/'client/screen143.sfc').read_bytes()))
 for exe,args in [('vlib',['work']),('vlog',['-sv','nes_screen_bus137.sv','screen137_bus_tb.sv']),('vsim',['-c','screen137_bus_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (o/(exe+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(o/(exe+'.log')).read_text(errors='replace');assert r.returncode==0 and '** Fatal:' not in s,exe
 assert 'PASS137 BUS rom_bytes=65536' in s
 result=dict(passed=True,rom_bytes=65536,source_sha256=sha(o/'nes_screen_bus137.sv'),program_sha256=sha(o/'screen-program.hex'),physical=False)
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS143 full64KiB bus mapping')
if __name__=='__main__':main()
