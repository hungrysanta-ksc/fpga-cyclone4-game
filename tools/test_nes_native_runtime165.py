# SPDX-License-Identifier: MIT
"""Integrated C runtime; captured native SPI and a synthetic sink ACK endpoint."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_game147 import ROOT,sha
from build_nes_game164 import palette

MODULES=['nes_native165','nes_native_video165','nes_native_sink165','nes_sink_spi165','nes_native_runtime165']

def main():
 p=argparse.ArgumentParser()
 for n in ['trace','out','gcc','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['trace','out','gcc','arm_bin']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False)
 fw=ROOT/'src/nes/firmware';sources={}
 for n in MODULES:
  for ext in ['c','h']:
   f=fw/(n+'.'+ext);shutil.copy2(f,a.out/f.name);sources[f.relative_to(ROOT).as_posix()]=sha(f)
 test=ROOT/'tests/nes-functional/native_runtime165_host.c';shutil.copy2(test,a.out/test.name)
 sources[test.relative_to(ROOT).as_posix()]=sha(test)
 shutil.copy2(__file__,a.out/'executed-test.py');shutil.copy2(a.trace,a.out/'native-transactions.txt')
 (a.out/'palette.bin').write_bytes(palette())
 def run(exe,args,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  assert r.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')[-3500:]
 run(a.gcc,['-std=c11','-O2','-Wall','-Wextra','-Werror',test.name,*[n+'.c' for n in MODULES],'-o','runtime.exe'],'gcc')
 run(a.out/'runtime.exe',['native-transactions.txt','palette.bin'],'host')
 for n in MODULES:
  run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-mcpu=cortex-m4','-mthumb','-Os','-Wall','-Wextra','-Werror','-fstack-usage','-c',n+'.c','-o',n+'.o'],n+'-arm')
 (a.out/'layout.c').write_text('#include "nes_native_runtime165.h"\nchar runtime_size[sizeof(struct nes_native_runtime165)];\nchar receiver_size[sizeof(struct nes_native165)];\nchar video_size[sizeof(struct nes_native_video165)];\n')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-mcpu=cortex-m4','-mthumb','-c','layout.c','-o','layout.o'],'layout')
 run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','--radix=d','layout.o'],'layout-size')
 result=dict(passed=True,cases=10,invalid_limit_rejected=True,trace_sha256=sha(a.trace),public_sources=sources,scope='Actual C receiver/converter/sink/CRC/runtime composed. Native responses replay prior RTL capture; sink ACK is synthetic. Not new physical SPI/SNES or real-time FPS proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
