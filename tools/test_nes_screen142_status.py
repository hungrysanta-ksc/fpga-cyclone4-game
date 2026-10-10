# SPDX-License-Identifier: MIT
"""Host-domain milestones and SPI snapshot; no electrical timing claim."""
from pathlib import Path
import argparse,json,shutil,subprocess,os
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','candidate']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 for n in ['nes_screen_status142.sv','nes_screen_bus137.sv','screen-program.hex']:shutil.copy2(a.candidate/n,o/n)
 shutil.copy2(ROOT/'tests/nes-functional/screen142_status_tb.sv',o/'screen142_status_tb.sv')
 shutil.copy2(ROOT/'tests/nes-functional/screen137_bus_tb.sv',o/'screen137_bus_tb.sv')
 (o/'screen-full.hex').write_text(''.join(f'{x:02x}\n' for x in (a.candidate/'client/screen142.sfc').read_bytes()))
 for tool,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv','nes_screen_status142.sv','nes_screen_bus137.sv','screen142_status_tb.sv','screen137_bus_tb.sv'],'compile'),('vsim',['-c','screen142_status_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'status'),('vsim',['-c','screen137_bus_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'bus')]:
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=(o/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and '** Fatal:' not in t,(label,t[-2000:])
 for n,text in [('status','PASS142 STATUS'),('bus','PASS137 BUS rom_bytes=65536')]:assert text in (o/(n+'.log')).read_text()
 (o/'result.json').write_text(json.dumps(dict(passed=True,rom_bytes=65536,source_sha256=sha(o/'nes_screen_status142.sv'),physical=False),indent=2)+'\n')
 print('PASS142 status and full SNES program/atlas/vector bus mapping')
if __name__=='__main__':main()
