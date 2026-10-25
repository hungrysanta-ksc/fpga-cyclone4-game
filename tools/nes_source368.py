# SPDX-License-Identifier: MIT
"""ARM-only causal frontier completion and byte-table source CRC; RTL unchanged."""
import re,shutil
from nes_delta231 import ROOT,BASE,once
from probe_nes_refill267 import run
FILES=['nes_planner285.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_delta231.c',
       'nes_output264.c','nes_refill267.c','nes_irq284.c','nes_bind287.c','nes_native289.c','stubs.s','libgcc.a']

def apply(d,fast=True):
 p=d/'nes_decode280.c';s=p.read_text()
 s=once(s,(ROOT/'tools/nes_source367.c').read_text(),(ROOT/'tools/nes_source368.c').read_text())
 if fast:
  table=[]
  for b in range(256):
   c=b<<8
   for _ in range(8):c=((c<<1)^0x1021 if c&32768 else c<<1)&65535
   table.append(c)
  start=s.index('static const uint16_t ct[16]');end=s.index('static uint16_t u16(',start)
  s=s[:start]+'static const uint16_t ct368[256]={\n'+',\n'.join(','.join(f'0x{x:04x}' for x in table[i:i+16]) for i in range(0,256,16))+'''};
uint16_t crc_source368(uint16_t c,uint8_t b){return (uint16_t)(c<<8)^ct368[((c>>8)^b)&255];}
static uint16_t crc(uint16_t c,uint8_t b){return crc_source368(c,b);}
'''+s[end:]
  s=s.replace('crc(c,','crc_source368(c,').replace('crc(s->checksum,','crc_source368(s->checksum,')
  assert s.count('crc(')==1
 p.write_text(s,newline='\n')

def compile_arm(d):
 arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 run(arm/'arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,layout.ld','-Wl,-Map,output.map',*FILES,'-o','output.elf'],d,'build368')
 run(arm/'arm-none-eabi-size.exe',['output.elf'],d,'size368')
 run(arm/'arm-none-eabi-objdump.exe',['-dr','output.elf'],d,'disassembly368')

def copy_build(reference,d,fast=True):
 d.mkdir(parents=True,exist_ok=False)
 for f in reference.iterdir():
  if f.is_file() and f.suffix in ('.c','.h','.inc','.a','.s','.ld'):shutil.copyfile(f,d/f.name)
 apply(d,fast);compile_arm(d)
