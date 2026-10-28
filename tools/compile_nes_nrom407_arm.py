# SPDX-License-Identifier: MIT
"""Compile actual 227 and generated loader with same Cortex-M4 options.

Object/stack comparison only: no full firmware link, IRQ runtime or timing.
"""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src'
bindir=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
gcc=bindir/'arm-none-eabi-gcc.exe';size=bindir/'arm-none-eabi-size.exe'
base=['-std=gnu99','-Os','-mthumb','-mcpu=cortex-m4','-mfloat-abi=hard','-fstack-usage',
      '-Wall','-Wstrict-prototypes','-Werror','-Wno-strict-aliasing','-DF_OSC=8000000UL',
      '-DGBC_DIAGNOSTIC','-DGBC_PROBE_G12','-DGBC_SAVE_G12','-DGBC_DUMP_G12']
includes=[str(x) for x in (a.build,prod,prod/'include',prod/'include/arm',prod/'obj-nes-100',prod/'stm32f4xx')]
incs=sum((['-I',x] for x in includes),[])
sources={'reference':prod/'nes_h1_stm32.c','candidate':a.build/'nes_h1_stm32.c',
         'layout':a.build/'nes_nrom406.c','verify':a.build/'nes_rom_verify.c'}
for name,source in sources.items():
 with(d/(name+'.log')).open('wb') as f:
  r=subprocess.run([str(gcc),*base,*incs,'-c',str(source),'-o',str(d/(name+'.o'))],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')
with(d/'size.log').open('wb') as f:
 r=subprocess.run([str(size),*[str(d/(name+'.o')) for name in sources]],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0
report={'passed':True,'scope':'individual Cortex-M4 objects and per-function stack only; no full link or cycles',
        'sources':{n:sha(q) for n,q in sources.items()},'compiler':sha(gcc),'size_output':(d/'size.log').read_text(),
        'stack_files':{n:(d/(n+'.su')).read_text() for n in sources}}
(d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'passed':True,'scope':report['scope'],'size_output':report['size_output']}))
