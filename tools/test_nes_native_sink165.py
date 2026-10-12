# SPDX-License-Identifier: MIT
"""Run real C producer concurrently with real SNES receiver over file bus model."""
from pathlib import Path
import argparse,json,subprocess,os
from nes_game147 import ROOT,sha
from build_nes_sink165 import build

def main():
 p=argparse.ArgumentParser()
 for n in ['video','out','gcc','arm-bin','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['video','out','gcc','arm_bin','mesen']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False)
 def run(exe,args,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')[-3000:]
 fw=ROOT/'src/nes/firmware'
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,fw/'nes_native_sink165.c',ROOT/'tests/nes-functional/native_sink165_host.c','-o','producer.exe'],'gcc')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c',fw/'nes_native_sink165.c','-o','sink.o'],'arm')
 run(a.arm_bin/'arm-none-eabi-size.exe',['sink.o'],'arm-size')
 (a.out/'layout.c').write_text('#include "nes_native_sink165.h"\nchar sink_context_size[sizeof(struct nes_native_sink165)];\n')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-mcpu=cortex-m4','-mthumb','-I',fw,'-c','layout.c','-o','layout.o'],'arm-layout')
 run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','--radix=d','layout.o'],'arm-layout-size')
 result=build(a.out/'client');cases=[]
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 for mode in ['normal','stop']:
  d=a.out/mode;d.mkdir()
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
  (d/'capture.lua').write_text(lua)
  with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
   producer=subprocess.Popen([str(a.out/'producer.exe'),str(a.video/'frame12'),str(a.video/'frame15'),mode],cwd=d,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   emulator=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,cwd=d,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:
    er=emulator.wait(timeout=70);cr=producer.wait(timeout=17)
   finally:
    for child in [emulator,producer]:
     if child.poll() is None:child.kill();child.wait()
  assert er==0 and cr==0,((d/'mesen.log').read_text(errors='replace')[-4000:],(d/'producer.log').read_text(errors='replace')[-2000:])
  q=json.loads((d/'consumer-result.json').read_bytes());assert q['passed']
  for i in range(1,q['commits']+1):assert (d/f'frame-{i}.rgb').read_bytes()==(a.video/f'expected-{min(i,2)}.rgb').read_bytes(),(mode,i)
  rows=[list(map(int,s.split())) for s in (d/'bus.tsv').read_text().splitlines()]
  assert len(rows)==q['acks']
  if mode=='normal':
   displayed=[row for row in rows if row[3]==1];assert [(r[4],r[5]) for r in displayed]==[(6,5493),(2,18),(0,0)]
   assert rows[-1][3]==0xe0
  else:assert rows[-1][3]==0xe4
  q.update(mode=mode,packet_bytes=sum(f.stat().st_size for f in d.glob('req-*.bin')),ack_bytes=q['acks']*12,last_status=rows[-1][3]);cases.append(q)
 sources=['src/nes/firmware/nes_native_sink165.h','src/nes/firmware/nes_native_sink165.c','tests/nes-functional/native_sink165_host.c','tools/build_nes_sink165.py','tools/test_nes_native_sink165.py','snes/video_probe/capture_native_sink165.lua','tools/nes_native_local165.py','tools/nes_spc163.py','tools/build_nes_trace_replay.py']
 inputs={f.relative_to(a.video).as_posix():sha(f) for folder in ['frame12','frame15'] for f in (a.video/folder).iterdir() if f.is_file()}
 for i in [1,2]:inputs[f'expected-{i}.rgb']=sha(a.video/f'expected-{i}.rgb')
 result.update(passed=True,cases=cases,public_sources={n:sha(ROOT/n) for n in sources},inputs=inputs,actual_c_and_snes_roundtrip=True,bus_model=True,physical_spi_binding=False,hardware_package=False,scope='Concurrent C packet producer and actual SNES CPU/SPC/WRAM/PPU. File model represents immutable hardware mailbox; no physical SPI/FPGA bridge, full MCU link, board timing or FPS proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
