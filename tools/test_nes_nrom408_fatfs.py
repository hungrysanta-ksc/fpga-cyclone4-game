# SPDX-License-Identifier: MIT
"""Exact full 407 loader with byte-identical 227 FatFS on synthetic FAT16.

FPGA/SPI/PSRAM and display remain explicit C models, not RTL cosimulation.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src'; host=BASE/'probes/nes-run136/evidence/initial/host04'
for q in host.glob('*.h'):shutil.copyfile(q,d/q.name)
for n in ('ff.c','ff.h','ffconf.h','diskio.h'):
 assert sha(host/n)==sha(prod/n),n
 shutil.copyfile(prod/n,d/n)
(d/'unicode').mkdir();shutil.copyfile(prod/'ccsbcs.c',d/'unicode/ccsbcs.c')
s=(a.build/'nes_h1_stm32.c').read_text()
helpers=s[s.index('static uint32_t load_crc('):s.index('\nbool nes_mcu_load_probe(')]
sd=s[s.index('static bool sd_query('):s.index('\n\n#include "nes_cf86_session094.h"')]
probe=s[s.index('bool nes_menu_sd_probe('):]
(d/'full408.inc').write_text(helpers+'\n'+sd+'\n'+probe,newline='\n')
tests=ROOT/'tests/nes-nrom408';gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
args=[gcc,'-std=c99','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function',
      '-Wno-sign-compare','-Wno-format','-ffunction-sections','-fdata-sections','-DNROM_USE_FATFS',
      '-I',str(d),'-I',str(a.build),'-I',str(prod),str(d/'ff.c'),str(d/'unicode/ccsbcs.c'),
      str(a.build/'nes_rom_verify.c'),str(prod/'nes_rom_spi.c'),str(a.build/'nes_nrom406.c'),
      str(tests/'fat_disk.c'),str(tests/'full_tb.c'),'-Wl,--gc-sections','-o',str(d/'test.exe')]
with(d/'compile.log').open('wb') as f:r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'compile.log').read_text(errors='replace')[-9000:]
with(d/'test.log').open('wb') as f:r=subprocess.run([str(d/'test.exe')],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
assert r.returncode==0 and 'NROM408 COMPLETE 227 loader function actual FatFS' in (d/'test.log').read_text(),(d/'test.log').read_text(errors='replace')
result={'passed':True,'loader':sha(a.build/'nes_h1_stm32.c'),'verify':sha(a.build/'nes_rom_verify.c'),
        'FatFS_source':sha(prod/'ff.c'),'FatFS_header':sha(prod/'ff.h'),'disk_test':sha(tests/'fat_disk.c'),
        'test':sha(tests/'full_tb.c'),'case_count':9,
        'scope':'full generated 227 loader + byte-identical 227 FatFS on synthetic FAT16, modeled SPI/PSRAM and run/base, no FPGA RTL cosimulation or physical hardware'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
