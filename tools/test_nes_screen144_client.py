# SPDX-License-Identifier: MIT
"""Execute144's65816 program and compare exact RGB with decoded actual-core packets."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_screen144 import ROOT,put,sha
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert,display_rgb
def main():
 p=argparse.ArgumentParser()
 for n in ['client','packets','chr-hex','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['normal','bad_length','bad_header'],default='normal')
 a=p.parse_args();o=a.out;assert str(o).isascii() and not o.exists();o.mkdir()
 data=b''.join((a.packets/f'packet-{i}.bin').read_bytes() for i in range(1,4));(o/'packets.bin').write_bytes(data)
 lua='local OUT_DIR='+json.dumps(o.as_posix())+'\nlocal PACKET_FILE='+json.dumps((o/'packets.bin').as_posix())+'\nlocal MODE='+json.dumps(a.mode)+'\n'
 put(o/'capture.lua',lua+(ROOT/'snes/video_probe/capture_screen144.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (o/'mesen.log').open('wb') as f:r=subprocess.run([str(a.mesen),'--testRunner',str(o/'capture.lua'),str(a.client/'screen144.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,'mesen.log'
 rows=[list(map(int,s.split())) for s in (o/'frames.tsv').read_text().splitlines()]
 model=list(map(int,(o/'model.tsv').read_text().split()))
 if a.mode=='normal':
  assert model==[3,6024,0],model
  assert len(rows)==3 and [r[1] for r in rows]==[1,2,3],rows
  atlas=convert(bytes(int(v,16) for v in a.chr_hex.read_text().split())).ljust(32768,b'\0');lut=display_rgb()
  for i,page,error,w,h,frame in rows:
   assert (error,w,h)==(0,256,239)
   expected=b''.join(lut[x] for x in decode(data[(i-1)*2008:i*2008],atlas)[:239*256])
   actual=(o/f'frame-{i}.rgb').read_bytes();assert actual==expected,(i,sum(x!=y for x,y in zip(actual,expected)))
  phases=[list(map(int,s.split()[1:])) for s in (o/'trace.tsv').read_text().splitlines() if s.startswith('PHASE')]
  starts=[x for x in phases if x[1]==1];ends=[x for x in phases if x[1]==3]
  assert len(starts)==len(ends)==3
  margins=[]
  for index,(start,end) in enumerate(zip(starts,ends)):
   # SETINI overscan is latched on the next frame. The initial transfer may
   # start in the225-line vblank while startup force-blank is still active.
   assert (225 if index==0 else 240)<=start[4]<=end[4]<=261
   margin=(262-start[4])*1364-4-start[5]-(end[2]-start[2]);assert margin>0;margins.append(margin)
 else:
  assert len(rows)==1
  assert model==([0,0,2] if a.mode=='bad_length' else [0,2008,7]),model
  margins=[]
 put(o/'result.json',json.dumps(dict(passed=True,mode=a.mode,frames=rows,model=model,ppu_margin_master_clocks=margins,
   inputs={n:sha(v) for n,v in {'rom':a.client/'screen144.sfc','packets':o/'packets.bin','mesen':a.mesen,'lua':o/'capture.lua'}.items()},
   comparison_phases_exact_rgb=0,scope='Actual SNES CPU/PPU/DMA with Lua packet MMIO model; not simultaneous RTL co-simulation or physical SNES.'),indent=2)+'\n')
 print('PASS144 client '+a.mode)
if __name__=='__main__':main()
