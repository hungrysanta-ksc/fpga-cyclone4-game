# SPDX-License-Identifier: MIT
"""Actual 227 sink and 65816 execute one RTL-derived frame; tile bus modeled."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
r=json.loads((a.rtl/'result.json').read_text());assert r['passed'] and r['blocks_sha256']==sha(a.rtl/'nrom429-blocks.txt') and r['fixture_sha256']==sha(a.rom)
prev=BASE/'probes/nes-repeat227/snes04';src=prev/'candidate';prod=BASE/'probes/nes-repeat227/arm01/src'
for n in ('nes_native_sink165.c','nes_native165.c','nes_planner211.c','nes_resident211.c'):
 assert sha(src/n)==sha(prod/n),n
for q in src.iterdir():
 if q.is_file() and q.suffix in ('.c','.h','.inc'):shutil.copyfile(q,d/q.name)
shutil.copyfile(prod/'nes_palette165.inc',d/'nes_palette165.inc');shutil.copyfile(ROOT/'tests/nes-nrom431/host.c',d/'host431.c');shutil.copyfile(a.rtl/'nrom429-blocks.txt',d/'blocks.txt');shutil.copyfile(a.rom,d/'fixture.nes')
lua=(prev/'candidate-normal/capture.lua').read_text(encoding='utf-8').split('\n',1)[1];(d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\n'+lua,encoding='utf-8')
exe=prev/'client/sink165.sfc';assert exe.is_file();gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
with(d/'build.log').open('wb') as f:q=subprocess.run([str(gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','host431.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_native_sink165.c','nes_sink_trace168.c','-o','host431.exe'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
assert q.returncode==0,(d/'build.log').read_text(errors='replace')[-3000:]
with(d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
 h=subprocess.Popen([str(d/'host431.exe'),'blocks.txt','fixture.nes'],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 m=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(exe),'--timeout=120','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:mr=m.wait(timeout=130);hr=h.wait(timeout=10)
 finally:
  for child in (h,m):
   if child.poll() is None:child.kill();child.wait()
assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-3000:],(d/'host.log').read_text(errors='replace')[-3000:])
c=json.loads((d/'consumer-result.json').read_text());assert c['passed'] and c['commits']==1 and c['retired_chunks']>=2
pixels=(d/'frame-1.rgb').read_bytes();assert len(pixels)==256*239*3
for y in range(16,224):
 for x in range(16,240):
  i=(y*256+x)*3;assert (pixels[i:i+3]==bytes(3)) == ((x+y)%2==0),(x,y,pixels[i:i+3])
host=(d/'host.log').read_text();assert 'PASS 227 sink display generation=4' in host
result={'passed':True,'fixture_sha256':sha(a.rom),'rtl_blocks_sha256':sha(a.rtl/'nrom429-blocks.txt'),'client_sha256':sha(exe),'host_output':host.strip(),'consumer':c,'checker_pixels':208*224,'frame_sha256':sha(d/'frame-1.rgb'),'scope':'actual 227 receiver/planner/sink and 65816 emulator with RTL-derived frame and modeled tile/packet bus; no live FPGA coupling, ARM timing, physical console or base restoration'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
