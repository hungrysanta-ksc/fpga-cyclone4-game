# SPDX-License-Identifier: MIT
"""Exercise actual generated 407 SPI controller using serial status/STOP."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
d.mkdir(parents=True);test=ROOT/'tests/nes-nrom407/spi_tb.sv'
shutil.copyfile(a.build/'nes_rom_spi.sv',d/'nes_rom_spi.sv');shutil.copyfile(test,d/'spi_tb.sv')
exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
for label,tool,args in [('vlib','vlib',['work']),('vlog','vlog',['-sv','nes_rom_spi.sv','spi_tb.sv']),
                        ('simulation','vsim',['-c','work.spi_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
 with(d/(label+'.log')).open('wb') as f:
  r=subprocess.run([str(exe/(tool+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(label+'.log')).read_text(errors='replace')
log=(d/'simulation.log').read_text(errors='replace')
assert 'NROM407 SPI PASS' in log and 'Errors: 0, Warnings: 0' in log
report={'passed':True,'RTL':sha(a.build/'nes_rom_spi.sv'),'test':sha(test),
        'scope':'real serial status ID and STOP pulse in idle, standalone controller; not whole loader/reset/base recovery'}
(d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report))
