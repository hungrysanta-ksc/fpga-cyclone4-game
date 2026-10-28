# SPDX-License-Identifier: MIT
"""Test exact generated 227 sd_source plus verify code with modeled IO."""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

p=argparse.ArgumentParser()
p.add_argument('--build',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args()
a.build=a.build.resolve()
d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists()
d.mkdir(parents=True)
src=(a.build/'nes_h1_stm32.c').read_text()
first=src[src.index('static uint32_t load_crc('):src.index('\nbool nes_mcu_load_probe(')]
second=src[src.index('struct sd_source_context {'):src.index('\n\n#include "nes_cf86_session094.h"')]
(d/'source407.inc').write_text(first+'\n'+second+'\n',newline='\n')
prod=BASE/'probes/nes-repeat227/arm01/src'
test=ROOT/'tests/nes-nrom407/source_tb.c'
args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
      '-std=c99','-O2','-Wall','-Wextra','-Werror','-I',str(d),'-I',str(a.build.resolve()),'-I',str(prod),
      str(a.build/'nes_rom_verify.c'),str(prod/'nes_rom_spi.c'),str(a.build/'nes_nrom406.c'),str(test),'-o',str(d/'test.exe')]
with (d/'compile.log').open('wb') as f:
    r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'compile.log').read_text(errors='replace')
with (d/'test.log').open('wb') as f:
    r=subprocess.run([str(d/'test.exe')],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0 and 'NROM407 actual sd_source and verifier PASS' in (d/'test.log').read_text()
result={'passed':True,'generated_loader':sha(a.build/'nes_h1_stm32.c'),
        'exact_extracted_functions':sha(d/'source407.inc'), 'generated_verify':sha(a.build/'nes_rom_verify.c'),
        'actual_227_spi_frame':sha(prod/'nes_rom_spi.c'),'test':sha(test),
        'scope':'actual generated sd_source+verify, synthetic file/SPI/PSRAM; no full 227 loader, hardware STOP or base recovery'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print(json.dumps(result))
