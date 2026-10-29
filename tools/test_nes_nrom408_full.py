# SPDX-License-Identifier: MIT
"""Execute exact full generated 227 loader with explicit modeled peers."""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
s=(a.build/'nes_h1_stm32.c').read_text()
helpers=s[s.index('static uint32_t load_crc('):s.index('\nbool nes_mcu_load_probe(')]
sd=s[s.index('static bool sd_query('):s.index('\n\n#include "nes_cf86_session094.h"')]
probe=s[s.index('bool nes_menu_sd_probe('):]
(d/'full408.inc').write_text(helpers+'\n'+sd+'\n'+probe,newline='\n')
prod=BASE/'probes/nes-repeat227/arm01/src';test=ROOT/'tests/nes-nrom408/full_tb.c'
args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
      '-std=c99','-O2','-Wall','-Wextra','-Werror','-I',str(d),'-I',str(a.build),'-I',str(prod),
      str(a.build/'nes_rom_verify.c'),str(prod/'nes_rom_spi.c'),str(a.build/'nes_nrom406.c'),str(test),'-o',str(d/'test.exe')]
with(d/'compile.log').open('wb') as f:r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'compile.log').read_text(errors='replace')
with(d/'test.log').open('wb') as f:r=subprocess.run([str(d/'test.exe')],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
assert r.returncode==0 and 'NROM408 COMPLETE' in (d/'test.log').read_text(),(d/'test.log').read_text(errors='replace')
result={'passed':True,'loader':sha(a.build/'nes_h1_stm32.c'),'extracted_exact_function_and_helpers':sha(d/'full408.inc'),
        'verify':sha(a.build/'nes_rom_verify.c'),'test':sha(test),'case_count':9,
        'scope':'entire generated 227 loader, verify/framing; modeled FatFS API, SPI/PSRAM, RUN/STOP and base; no actual FPGA RTL or hardware'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
