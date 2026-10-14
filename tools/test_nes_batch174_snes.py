# SPDX-License-Identifier: MIT
"""Batched C packets -> existing172 actual65816 receiver, pixel/ACK/STOP check.

File mailbox model, not physical SPI, MCU speed, or FPS measurement.
"""
from pathlib import Path
import argparse,json,os,subprocess,shutil
from nes_game147 import ROOT,sha
from nes_batch174 import replace

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','pixels','client','out','gcc','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in vars(a):setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False)
 assert sha(a.client/'sink-program.hex')=='e1c350b76fea340a1ed9fa643929ce80bd0371b748b374d57ce8d90d85188fc5'
 for n in ['nes_native_sink165.c','nes_native_sink165.h','nes_native_video165.h','nes_native165.h','nes_sink_trace168.c','nes_sink_trace168.h']:
  shutil.copy2(a.arm/'src'/n,a.out/n)
 s=(ROOT/'tests/nes-functional/native_sink165_host.c').read_text()
 for kind,section,stride,cap in [(0,'bg',16,15),(1,'obj',32,7)]:
  s=replace(s,f' for(unsigned i=0;i<{section};i++)assert(nes_sink165_pattern(&s,{kind},i,pattern+i*{stride},{stride}));',
   f' for(unsigned i=0;i<{section};){{unsigned n={section}-i;if(n>{cap})n={cap};assert(nes_sink165_pattern(&s,{kind},i,pattern+i*{stride},n*{stride}));i+=n;}}')
 (a.out/'producer.c').write_text(s,encoding='utf8',newline='\n')
 with (a.out/'compile.log').open('wb') as f:
  q=subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I.','producer.c','nes_native_sink165.c','nes_sink_trace168.c','-o','producer.exe'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
 assert q.returncode==0,(a.out/'compile.log').read_text()
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 cases=[]
 for mode in ['normal','stop']:
  d=a.out/mode;d.mkdir()
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
  (d/'capture.lua').write_text(lua,encoding='utf8',newline='\n')
  with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
   c=subprocess.Popen([str(a.out/'producer.exe'),str(a.pixels/'frame24'),str(a.pixels/'frame25'),mode],cwd=d,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.client/'sink165.sfc'),'--timeout=90','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=100);cr=c.wait(timeout=20)
   finally:
    for child in [m,c]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==cr==0,((d/'mesen.log').read_text()[-3000:],(d/'producer.log').read_text()[-1000:])
  q=json.loads((d/'consumer-result.json').read_bytes());assert q['passed']
  for i in range(1,q['commits']+1):assert (d/f'frame-{i}.rgb').read_bytes()==(a.pixels/f'expected-{min(i,2)}.rgb').read_bytes(),(mode,i)
  packets=[f.read_bytes() for f in sorted(d.glob('req-*.bin'))]
  lengths=[len(b)-16 for b in packets if b[0]==2 and b[1]<2]
  assert 240 in lengths and 64 in lengths and max(lengths)==240,lengths
  q.update(mode=mode,pattern_lengths=lengths,request_bytes=sum(map(len,packets)),ack_bytes=q['acks']*12);cases.append(q)
  print(json.dumps(q),flush=True)
 r=dict(passed=True,cases=cases,pixels=229376,scope=__doc__,client_sha256=sha(a.client/'sink165.sfc'),
  sources={n.name:sha(n) for n in a.out.glob('*.[ch]')},
  inputs={f.relative_to(a.pixels).as_posix():sha(f) for f in a.pixels.rglob('*') if f.is_file() and (f.parent.name in ['frame24','frame25'] or f.name.startswith('expected-'))},
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_batch174_snes.py','tests/nes-functional/native_sink165_host.c','snes/video_probe/capture_native_sink165.lua','tools/nes_batch174.py']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
