# SPDX-License-Identifier: MIT
"""Compile/execute the exact M4 compact planner on recorded received-map fixtures.
Only prepares native CPU inputs;live390 ARM must independently match these bytes.
"""
import argparse,json,shutil,struct,subprocess
from pathlib import Path
from probe_nes_arm264 import ARM
from probe_nes_spool383 import fixtures
from nes_delta231 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(ROOT/'tools/nes_compact390.c',d/'plan.c')
 (d/'stub.c').write_text('#include <stdint.h>\nvoid *memset(void *p,int v,unsigned n){uint8_t *q=p;while(n--)*q++=v;return p;}\nuint8_t bits390[256],packet390[192];unsigned map_byte327(unsigned i){return bits390[i];}\n')
 (d/'unit.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) } }\n')
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 for name,args,log in [('arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,unit.ld','-Wl,-e,step_plan390','plan.c','stub.c','-o','unit.elf'],'build'),('arm-none-eabi-size.exe',['unit.elf'],'size'),('arm-none-eabi-objdump.exe',['-dr','unit.elf'],'disassembly')]:
  r=subprocess.run([str(tool/name),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/(log+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
 rows=[]
 for f in range(907,917):
  bits=bytearray(256)
  for j in fixtures(f):
   desc=bytes.fromhex(j['descriptor'])
   if j['typed']and desc[0]&2:
    first=int.from_bytes(desc[3:5],'little');count=len(bytes.fromhex(j['data']))//2
    for w in range(first,first+count):bits[w//8]|=1<<(w%8)
  arm=ARM(d/'unit.elf',None);arm.symbols.update(io259=0x0800f000,trace259=0x0800f004);arm.uc.mem_write(arm.symbols['bits390'],bytes(bits));arm.call('reset_plan390',[]);steps=[]
  while True:
   before=arm.instructions;n=arm.call('step_plan390',[arm.symbols['packet390']]);steps.append(arm.instructions-before)
   if n:break
   assert len(steps)<=21
  b=bytearray(arm.uc.mem_read(arm.symbols['packet390'],n));b[4]=(f-905)%2;b[6:8]=struct.pack('<H',f-904);b[8:12]=struct.pack('<I',f-904)
  (d/f'plan{f}.bin').write_bytes(b);(d/f'map{f}.bin').write_bytes(bits)
  rows.append(dict(frame=f,mode=b[3],bytes=n,ranges=int.from_bytes(b[12:14],'little'),words=int.from_bytes(b[14:16],'little'),instructions=sum(steps),steps=steps,stack=0x2003f000-arm.low_sp,plan=sha(d/f'plan{f}.bin')))
 (d/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,scope=__doc__,source=sha(ROOT/'tools/nes_compact390.c')),indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
