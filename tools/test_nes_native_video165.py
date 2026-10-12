# SPDX-License-Identifier: MIT
"""Bounded C compiler -> actual SNES model; reuses sealed real-game evidence."""
from pathlib import Path
import argparse,json,subprocess,os,struct,hashlib
from nes_game147 import ROOT,sha
from build_nes_game164 import palette
from nes_native_commands165 import Write
from test_nes_native_commands165 import build

def main():
 p=argparse.ArgumentParser()
 for n in ['scenes','out','gcc','arm-bin','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['scenes','out','gcc','arm_bin','mesen']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False)
 def run(exe,args,out,name,env=None):
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  log=(out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,log[-4000:];return log
 fw=ROOT/'src/nes/firmware';files=[fw/'nes_native165.c',fw/'nes_native_video165.c',ROOT/'tests/nes-functional/native_video165_host.c']
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,*files,'-o',a.out/'video.exe'],a.out,'gcc')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c',fw/'nes_native_video165.c','-o','video.o'],a.out,'arm')
 run(a.arm_bin/'arm-none-eabi-size.exe',['video.o'],a.out,'arm-size')
 raw=bytes(int(x,16) for x in (a.scenes/'chr.hex').read_text().split());plans=[];expected=[];results=[];old={};inputs={}
 for frame in [12,15]:
  d=a.out/f'frame{frame}';d.mkdir();path=a.scenes/f'frame-{frame}.dump';lines=path.read_text().splitlines();h=lines[0].split();assert h[1:3]==['1','00'];rows,groups,objects,exceptions=map(int,h[3:]);assert rows==224
  tables=[{} for _ in range(7)]
  for line in lines[1:]:k,i,v=line.split();tables[int(k)][int(i)]=int(v,16)
  npal=len(tables[5])//32;words=[];records=0;chrbytes=0
  def add(k,i,v):words.append((k<<93)|(frame<<77)|(i<<64)|v)
  add(7,0,(0x1651<<48)|(groups<<42)|(npal<<36)|(224<<28)|(objects<<20)|(exceptions<<12))
  for k in range(6):
   for i,v in sorted(tables[k].items()):add(k,i,v);records+=1
  for tile,kind in sorted(tables[6].items()):
   if kind:
    for lane in range(16):add(6,tile,(kind<<12)|(lane<<8)|raw[tile*16+lane]);records+=1;chrbytes+=1
  add(7,1,(records<<16)|chrbytes);add(7,3,0)
  (d/'records.hex').write_text(''.join(f'{v:024x}\n' for v in words));(d/'palette.bin').write_bytes(palette())
  log=run(a.out/'video.exe',['records.hex','palette.bin'],d,'receiver-video')
  size,bg,obj,ng,no,nh,hofs,vofs=map(int,(d/'summary.txt').read_text().split());writes=[];candidate={}
  for name,kind,address in [('bg','vram',0),('obj','vram',0x4000),('map','vram',0x8000),('cgram','cgram',0),('oam','oam',0),('hdma','hdma',0x9000)]:
   b=(d/(name+'.bin')).read_bytes();candidate[name]=b
   # PC test uploader only. No second full C candidate is required on MCU.
   if name not in old:
    if b:writes.append(Write(kind,address,b))
   elif kind=='vram':
    starts=[]
    for at in range(0,len(b),2):
     if b[at:at+2]!=old[name][at:at+2]:
      if starts and at-starts[-1][1]<=32:starts[-1][1]=at+2
      else:starts.append([at,at+2])
    writes.extend(Write(kind,address+start,b[start:end]) for start,end in starts)
   elif b!=old[name]:writes.append(Write(kind,address,b))
  old=candidate;payload=sum(len(w.data) for w in writes);charged=payload+96*len(writes)
  if plans:assert charged<=5000 and len(writes)<=32
  plans.append(dict(writes=writes,scroll_rows=[(hofs,vofs)]))
  lut=struct.unpack('<64H',palette());pixels=[int(x,16)&63 for x in (a.scenes/f'game-{frame}.hex').read_text().split()][8*256:232*256]
  rgb=b''.join(bytes((((lut[v]>>s)&31)<<3)|(((lut[v]>>s)&31)>>2) for s in [0,5,10]) for v in pixels)
  expected.append(bytes(7*256*3)+rgb+bytes(8*256*3));results.append(dict(frame=frame,plan_bytes=size,bg_patterns=bg,obj_patterns=obj,groups=ng,objects=no,payload=payload,commands=len(writes),charged=charged,c_test=log.strip()))
  inputs[f'frame-{frame}.dump']=sha(path);inputs[f'game-{frame}.hex']=sha(a.scenes/f'game-{frame}.hex')
 build(plans,a.out)
 (a.out/'capture.lua').write_text('local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_commands165.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 run(a.mesen,['--testRunner',a.out/'capture.lua',a.out/'native.sfc','--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],a.out,'mesen',env)
 for i,gold in enumerate(expected,1):
  actual=(a.out/f'frame-{i}.rgb').read_bytes();(a.out/f'expected-{i}.rgb').write_bytes(gold);assert actual==gold,(i,len(actual),sum(x!=y for x,y in zip(actual,gold)))
  results[i-1]['rgb_sha256']=hashlib.sha256(actual).hexdigest()
 trace=[list(map(int,l.split())) for l in (a.out/'trace.tsv').read_text().splitlines()];commit=next(x for x in trace if x[0]==0x7000 and x[1]==2);assert commit[3]>=225
 sources=['src/nes/firmware/nes_native_video165.h','src/nes/firmware/nes_native_video165.c','tests/nes-functional/native_video165_host.c','tools/test_nes_native_video165.py']
 result=dict(passed=True,frames=results,pixels=114688,commit_scanline=commit[3],inputs=inputs,chr_sha256=sha(a.scenes/'chr.hex'),public_sources={n:sha(ROOT/n) for n in sources},scope='Actual bounded C converts committed sealed real-game data; PC assembles uploads and real SNES CPU/DMA/PPU renders. ARM object only, not MCU loop, streaming upload, fit or board.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
