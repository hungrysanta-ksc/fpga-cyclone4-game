# SPDX-License-Identifier: MIT
"""Execute the actual65816 program; verify black/held intervals and exact pixels."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_screen145 import ROOT,put,sha
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert,display_rgb

def main():
 p=argparse.ArgumentParser()
 for n in ['client','packets','chr-hex','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['normal','mixed','bad_length','bad_header'],default='normal')
 a=p.parse_args();o=a.out;assert str(o).isascii() and not o.exists();o.mkdir()
 packets=[(a.packets/f'packet-{i}.bin').read_bytes() for i in range(1,4)]
 if a.mode=='mixed':
  # Deliberately mixed tilemap, valid packet: holding must not hide or repair it.
  first=bytearray(packets[0]);first[20+960:20+1920]=packets[1][20+960:20+1920]
  assert first[20:1940]!=packets[0][20:1940] and first[20:1940]!=packets[1][20:1940]
  packets[0]=bytes(first)
 data=b''.join(packets);(o/'packets.bin').write_bytes(data)
 lua='local OUT_DIR='+json.dumps(o.as_posix())+'\nlocal PACKET_FILE='+json.dumps((o/'packets.bin').as_posix())+'\nlocal MODE='+json.dumps(a.mode)+'\n'
 put(o/'capture.lua',lua+(ROOT/'snes/video_probe/capture_screen145.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (o/'mesen.log').open('wb') as f:r=subprocess.run([str(a.mesen),'--testRunner',str(o/'capture.lua'),str(a.client/'screen145.sfc'),'--timeout=90','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,'mesen.log'
 rows=[list(map(int,s.split())) for s in (o/'frames.tsv').read_text().splitlines()]
 model=list(map(int,(o/'model.tsv').read_text().split()))
 timing=[]
 if a.mode in ['normal','mixed']:
  assert model==[3,6024,0],model
  assert len(rows)==9 and [r[-1] for r in rows]==[3,90,175]*3,rows
  atlas=convert(bytes(int(v,16) for v in a.chr_hex.read_text().split())).ljust(32768,b'\0');lut=display_rgb()
  for i in range(1,4):
   expected=b''.join(lut[x] for x in decode(packets[i-1],atlas)[:239*256])
   for age in [3,90,175]:assert (o/f'frame-{i}-{age}.rgb').read_bytes()==expected,(i,age)
   assert (o/f'black-{i}.rgb').read_bytes()==bytes(256*239*3),i
   (o/f'frame-{i}.rgb').write_bytes(expected)
  trace=[(s.split()[0],list(map(int,s.split()[1:]))) for s in (o/'trace.tsv').read_text().splitlines()]
  phases=[v for k,v in trace if k=='PHASE']
  assert [v[1] for v in phases]==[1,3,4]*3,phases
  for i in range(3):
   black,shown,end=phases[i*3:i*3+3]
   assert shown[3]-black[3]>=90,(black,shown)
   assert end[3]-shown[3]>=180,(shown,end)
   assert (shown[2]-black[2])>21477272,(black,shown)
   # No PPU, DMA or MMIO writes occur between shown and hold-end markers.
   edits=[(k,v) for k,v in trace if k in ['PPU','DMA','W'] and shown[2]<v[-1 if k=='DMA' else 2]<end[2]]
   assert not edits,edits[:10]
   timing.append(dict(black_tv_frames=shown[3]-black[3],held_tv_frames=end[3]-shown[3],black_master_clocks=shown[2]-black[2],held_master_clocks=end[2]-shown[2]))
 else:
  assert len(rows)==1
  assert model==([0,0,2] if a.mode=='bad_length' else [0,2008,7]),model
 put(o/'result.json',json.dumps(dict(passed=True,mode=a.mode,frames=rows,model=model,timing=timing,
  held_rgb_samples=9 if timing else 0,black_rgb_samples=3 if timing else 0,
  no_ppu_dma_or_packet_write_during_hold=bool(timing),
  inputs={n:sha(v) for n,v in {'rom':a.client/'screen145.sfc','packets':o/'packets.bin','mesen':a.mesen,'lua':o/'capture.lua'}.items()},
  scope='Actual SNES CPU/PPU/DMA with Lua packet MMIO model; exact144 RTL packets reused. Not physical or concurrent whole-board simulation.'),indent=2)+'\n')
 print('PASS145 client '+a.mode)
if __name__=='__main__':main()
