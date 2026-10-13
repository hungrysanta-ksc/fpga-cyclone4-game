# SPDX-License-Identifier: MIT
"""Actual runtime/converter/CRC to actual SNES client via a file mailbox model."""
from pathlib import Path
import argparse,json,subprocess,os,shutil
from nes_game147 import ROOT,sha
from build_nes_game164 import palette
from build_nes_sink165 import build
from test_nes_native_runtime165 import MODULES
def main():
 p=argparse.ArgumentParser()
 for n in ['trace','expected','out','gcc','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in vars(a):setattr(a,n,getattr(a,n).resolve())
 assert a.out.as_posix().isascii(),'Use a fresh ASCII output path for Windows Lua file IO.'
 a.out.mkdir(parents=True,exist_ok=False);fw=ROOT/'src/nes/firmware'
 sources=[f'src/nes/firmware/{n}.{e}' for n in MODULES for e in ['c','h']]+['tests/nes-functional/native_coupled165_host.c','tools/test_nes_coupled165.py','tools/build_nes_sink165.py','snes/video_probe/capture_native_sink165.lua','tools/nes_native_local165.py','tools/nes_spc163.py','tools/build_nes_trace_replay.py','tools/build_nes_game164.py']
 (a.out/'sources').mkdir()
 for n in sources:shutil.copy2(ROOT/n,a.out/'sources'/Path(n).name)
 (a.out/'palette.bin').write_bytes(palette());shutil.copy2(a.trace,a.out/'native-transactions.txt');shutil.copy2(a.expected,a.out/'expected.rgb')
 with (a.out/'gcc.log').open('wb') as f:
  r=subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(fw),*[str(fw/(n+'.c')) for n in MODULES],str(ROOT/'tests/nes-functional/native_coupled165_host.c'),'-o',str(a.out/'producer.exe')],stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(a.out/'gcc.log').read_text()
 client=build(a.out/'client');cases=[];env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 base=(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
 assert base.count("assert(captured==(MODE=='stop' and 1 or 3))")==1
 base=base.replace("assert(captured==(MODE=='stop' and 1 or 3))","assert(captured==1)")
 for mode in ['normal','deadline']:
  d=a.out/mode;d.mkdir();(d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+base)
  with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
   c=subprocess.Popen([str(a.out/'producer.exe'),str(a.out/'native-transactions.txt'),str(a.out/'palette.bin'),mode],cwd=d,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=70);cr=c.wait(timeout=15)
   finally:
    for child in [m,c]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==cr==0,((d/'mesen.log').read_text(errors='replace')[-4000:],(d/'producer.log').read_text(errors='replace')[-2000:])
  producer=json.loads((d/'producer-result.json').read_bytes());consumer=json.loads((d/'consumer-result.json').read_bytes())
  assert producer['passed'] and consumer['passed'] and producer['acks']==consumer['acks']
  assert (d/'frame-1.rgb').read_bytes()==a.expected.read_bytes(),mode
  cases.append(dict(mode=mode,producer=producer,consumer=consumer,pixels=256*239,rgb_sha256=sha(d/'frame-1.rgb')))
 result=dict(passed=True,cases=cases,client=client,public_sources={n:sha(ROOT/n) for n in sources},inputs=dict(trace_sha256=sha(a.trace),expected_sha256=sha(a.expected),mesen_sha256=sha(a.mesen)),physical=False,hardware_package=False,scope='Actual runtime and real SNES generated ACK. Native source is prior RTL trace; E0/E1 filebus is a model. Deadline injected at real SEAL ACK return. Not physical SPI, new game boot, MCU cycle timing or FPS.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=cases)))
if __name__=='__main__':main()
