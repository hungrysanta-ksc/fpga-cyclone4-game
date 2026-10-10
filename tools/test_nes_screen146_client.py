# SPDX-License-Identifier: MIT
"""Actual65816/PPU cadence, complete pixels, and blank-contained uploads."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_screen146 import ROOT,put,sha
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert,display_rgb

def main():
 p=argparse.ArgumentParser()
 for n in ['client','packets','chr-hex','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['normal','mixed','late','bad_length','bad_header'],default='normal')
 a=p.parse_args();o=a.out;assert str(o).isascii() and not o.exists();o.mkdir()
 packets=[(a.packets/f'packet-{i}.bin').read_bytes() for i in range(1,4)]
 if a.mode=='mixed':
  first=bytearray(packets[0]);first[980:1940]=packets[1][980:1940];packets[0]=bytes(first)
 (o/'packets.bin').write_bytes(b''.join(packets))
 lua='local OUT_DIR='+json.dumps(o.as_posix())+'\nlocal PACKET_FILE='+json.dumps((o/'packets.bin').as_posix())+'\nlocal MODE='+json.dumps(a.mode)+'\n'
 put(o/'capture.lua',lua+(ROOT/'snes/video_probe/capture_screen146.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (o/'mesen.log').open('wb') as f:
  proc=subprocess.run([str(a.mesen),'--testRunner',str(o/'capture.lua'),str(a.client/'screen146.sfc'),'--timeout=90','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
 assert proc.returncode==0,'mesen.log'
 rows=[list(map(int,s.split())) for s in (o/'frames.tsv').read_text().splitlines()]
 model=list(map(int,(o/'model.tsv').read_text().split()))
 timing=[]
 if a.mode in ['normal','mixed','late']:
  assert model==[30,60240,0],model
  assert set(r[0] for r in rows)==set(range(1,31)),rows
  atlas=convert(bytes(int(v,16) for v in a.chr_hex.read_text().split())).ljust(32768,b'\0');lut=display_rgb()
  expected=[b''.join(lut[x] for x in decode(packet,atlas)[:239*256]) for packet in packets]
  for seq,page,err,w,h,frame in rows:
   assert not err and (w,h)==(256,239)
   assert (o/f'frame-{frame}.rgb').read_bytes()==expected[(seq-1)%3],(seq,frame)
  trace=[(s.split()[0],list(map(int,s.split()[1:]))) for s in (o/'trace.tsv').read_text().splitlines()]
  phases=[v for k,v in trace if k=='PHASE'];assert [v[1] for v in phases]==[1,3,4]*30
  for i in range(30):
   black,shown,end=phases[i*3:i*3+3];hold=30 if i<12 else 2
   assert end[3]-shown[3]>=hold,(i,shown,end)
   if a.mode=='late' and i==12:
    assert shown[3]==black[3]+1 and 225<=shown[4]<=240,(black,shown)
   else:
    assert black[3]==shown[3] and 225<=black[4]<=shown[4]<=260,(black,shown)
   edits=[(k,v) for k,v in trace if k in ['PPU','DMA','W'] and shown[2]<v[-1 if k=='DMA' else 2]<end[2]]
   assert not edits,edits[:5]
   timing.append(dict(packet=i+1,hold_frames=end[3]-shown[3],upload_master_clocks=shown[2]-black[2],start_line=black[4],reveal_line=shown[4]))
 else:
  assert len(rows)==1 and model==([0,0,2] if a.mode=='bad_length' else [0,2008,7]),model
 put(o/'result.json',json.dumps(dict(passed=True,mode=a.mode,model=model,exact_rgb_frames=len(rows) if timing else 0,timing=timing,inputs={n:sha(v) for n,v in {'rom':a.client/'screen146.sfc','packets':o/'packets.bin','mesen':a.mesen,'lua':o/'capture.lua'}.items()},scope='Actual SNES CPU/PPU/DMA with30 supplied packets, not concurrent FPGA or physical proof.'),indent=2)+'\n')
 print('PASS146 client',a.mode,len(rows))
if __name__=='__main__':main()
