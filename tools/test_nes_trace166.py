# SPDX-License-Identifier: MIT
"""Instrumented receiver + unchanged runtime tests and dirty-WRAM SNES boot."""
from pathlib import Path
import argparse,json,subprocess,shutil,os
from nes_game147 import ROOT,sha
from nes_trace166 import receiver
from test_nes_native_runtime165 import MODULES
from build_nes_game164 import palette
from build_nes_sink165 import build
def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc','mesen','trace','expected']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in vars(a):setattr(a,n,getattr(a,n).resolve())
 assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
 files=[f'src/nes/firmware/{n}.{e}' for n in MODULES+['nes_trace166'] for e in ['c','h']]+['tests/nes-functional/native_trace166_host.c','tests/nes-functional/native_runtime165_host.c','tests/nes-functional/native_coupled165_host.c','tools/nes_trace166.py','tools/test_nes_trace166.py','snes/video_probe/capture_native_sink165.lua']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 f=a.out/'nes_native165.c';f.write_text(receiver(f.read_text()))
 f=a.out/'native_coupled165_host.c';s=f.read_text();s='#include "nes_trace166.h"\n'+s
 anchor=' f=fopen("producer-done.txt","w");';assert s.count(anchor)==1
 s=s.replace(anchor,' assert(nes_trace166.begins==1&&nes_trace166.ends==1&&nes_trace166.commits==1&&nes_trace166.aborts==0&&nes_trace166.records>1000);\n'+anchor);f.write_text(s)
 shutil.copy2(a.trace,a.out/'native-transactions.txt');(a.out/'palette.bin').write_bytes(palette())
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def run(args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  assert r.returncode==0,(a.out/(label+'.log')).read_text(errors='replace')[-3500:]
 common=[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror']
 for bench in ['trace166','runtime165','coupled165']:
  run(common+[f'native_{bench}_host.c',*[n+'.c' for n in MODULES+['nes_trace166']],'-o',bench+'.exe'],bench+'-gcc')
 run([a.out/'trace166.exe'],'trace');run([a.out/'runtime165.exe','native-transactions.txt','palette.bin'],'runtime')
 build(a.out/'client');d=a.out/'dirty';d.mkdir()
 lua=(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text().replace("assert(captured==(MODE=='stop' and 1 or 3))","assert(captured==1)")
 # Before client boot, seed metadata, both bank7F candidates and scratch.
 # Client must explicitly initialize metadata and fully upload the first image.
 poison="for i=0,131071 do emu.write(i,(i*37+165)&255,emu.memType.snesWorkRam) end\n"
 (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE="normal"\n'+poison+lua)
 with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
  c=subprocess.Popen([str(a.out/'coupled165.exe'),str(a.out/'native-transactions.txt'),str(a.out/'palette.bin'),'normal'],cwd=d,env=env,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:mr=m.wait(timeout=70);cr=c.wait(timeout=15)
  finally:
   for child in [m,c]:
    if child.poll() is None:child.kill();child.wait()
 assert mr==cr==0,((d/'mesen.log').read_text(errors='replace'),(d/'producer.log').read_text(errors='replace'))
 assert (d/'frame-1.rgb').read_bytes()==a.expected.read_bytes()
 consumer=json.loads((d/'consumer-result.json').read_bytes());producer=json.loads((d/'producer-result.json').read_bytes())
 assert consumer['acks']==producer['acks']==45 and consumer['commits']==producer['frames']==1
 result=dict(passed=True,trace_bytes=48,runtime_cases=10,dirty_wram_bytes=131072,pixels=61184,producer=producer,consumer=consumer,public_sources={n:sha(ROOT/n) for n in files},inputs=dict(trace=sha(a.trace),expected=sha(a.expected),mesen=sha(a.mesen)),scope='Actual receiver/runtime and real SNES client. Both candidate WRAM banks and metadata seeded nonzero before boot. Exact first image and45ACK. Native SPI capture/filebus; not physical producer pacing, IO reset or FPS.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='public_sources'}))
if __name__=='__main__':main()
