# SPDX-License-Identifier: MIT
"""Production181 SNES decoder/DMA/HDMA/ACK with actual C sink, held file bus.
Reuses pinned C-produced consume181 scenes, not its direct-upload ROM/ACKs.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, struct, subprocess
from nes_client181 import build
import test_nes_patch181_snes as prototype
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def expected(count,phase):
 old=prototype.ROWS
 try:
  prototype.ROWS=old[:count] if phase<2 else [128+i*8 for i in range(7)]
  result=bytearray(prototype.expected(phase))
  if phase:
   value=struct.unpack('<64H',prototype.palette())[15]
   rgb=bytes((((value>>s)&31)<<3)|(((value>>s)&31)>>2) for s in (0,5,10))
   for y in range(224):
    if y not in prototype.ROWS:
     for x in range(8):result[((y+7)*256+x)*3:((y+7)*256+x)*3+3]=rgb
  return result
 finally:prototype.ROWS=old

def main():
 p=argparse.ArgumentParser()
 for n in ('out','gcc','mesen','fixtures'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--modes',default='normal,max,raw_first,version,count,count_mismatch,seal_size,mode,repeat,length,scroll,stop_copy,stop_final')
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 sources={}
 for src,name in [(ROOT/'src/nes/firmware/nes_native_sink181.c','nes_native_sink165.c'),
                  (ROOT/'src/nes/firmware/nes_native_video181.h','nes_native_video165.h'),
                  (ROOT/'src/nes/firmware/nes_native181.h','nes_native165.h'),
                  (ROOT/'tests/nes-functional/client181_host.c','host.c')]:
  shutil.copyfile(src,a.out/name);sources[str(src.relative_to(ROOT))]=sha(src)
 for name in ['nes_native_sink165.h','nes_sink_trace168.c','nes_sink_trace168.h']:
  shutil.copyfile(a.fixtures/name,a.out/name);sources['fixture/'+name]=sha(a.fixtures/name)
 for n in ['tools/nes_client181.py','tools/test_nes_client181.py','snes/video_probe/capture_client181.lua']:
  sources[n]=sha(ROOT/n);shutil.copyfile(ROOT/n,a.out/Path(n).name)
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'gcc.log').open('wb') as f:
  q=subprocess.run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','host.c','nes_native_sink165.c','nes_sink_trace168.c','-o','host.exe'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(a.out/'gcc.log').read_text()
 client=build(a.out/'client');results=[]
 for mode in a.modes.split(','):
  d=a.out/mode;d.mkdir()
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+(ROOT/'snes/video_probe/capture_client181.lua').read_text(),encoding='utf8')
  with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
   h=subprocess.Popen([str(a.out/'host.exe'),str(a.fixtures),mode],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=50','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=60);hr=h.wait(timeout=20)
   finally:
    for child in [h,m]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-3000:],(d/'host.log').read_text(errors='replace')[-1500:])
  frames=[(0,0),(7,0),(7,1),(0,0),(0,0),(1,0),(7,2)] if mode=='normal' else ([(0,0),(7,0)] if mode=='max' else [(0,0)])
  if mode=='raw_first':frames=[(7,0),(0,0)]
  for i,(count,phase) in enumerate(frames,1):
   actual=(d/f'frame-{i}.rgb').read_bytes();gold=expected(count,phase);(d/f'expected-{i}.rgb').write_bytes(gold)
   assert actual==gold,(mode,i,sum(x!=y for x,y in zip(actual,gold)))
  result=json.loads((d/'consumer-result.json').read_bytes());result['mode']=mode;results.append(result);print(json.dumps(result),flush=True)
 for n in ['tools/nes_boot172.py','tools/nes_banked169.py','tools/nes_clip178.py','tools/nes_native_local165.py','tools/build_nes_sink165.py','tools/nes_spc163.py','tools/build_nes_trace_replay.py','snes/video_probe/build_probe.py','tools/nes_patch181.py','tools/test_nes_patch181_snes.py','tools/build_nes_game164.py','src/renderer/base/g9_snes_io.py']:sources[n]=sha(ROOT/n)
 result=dict(passed=True,client=client,cases=results,sources=sources,fixture_files={f.relative_to(a.fixtures).as_posix():sha(f) for f in a.fixtures.glob('rows*/*') if f.is_file()},mesen_sha256=sha(a.mesen),hardware=False,full_arm_link=False,new_fit=False,scope='Actual C sink and production65816 mailbox/ACK with modeled held bus. Reused C scenes, not actual game/SPI/60fps.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print('PASS CLIENT181')
if __name__=='__main__':main()
