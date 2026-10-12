# SPDX-License-Identifier: MIT
"""C delta/ownership -> actual SNES WRAM DMA; no cartridge SRAM access."""
from pathlib import Path
import argparse,json,subprocess,os,struct
from nes_game147 import ROOT,sha
from build_nes_trace_replay import Code

def build(frames,out):
 c=Code(0x8000);data=bytearray()
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
 for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2106,0),(0x2107,0x41),(0x210b,0),(0x2101,1),(0x212c,0x11),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0),(0x2115,128)]:c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 def blank(name):
  c.label(name+'a');c.absolute(0xad,0x4212);c.branch(0x30,name+'a')
  c.label(name+'b');c.absolute(0xad,0x4212);c.branch(0x10,name+'b')
 def dma(src,n,port,mode):
  for a,v in [(0x4300,mode),(0x4301,port),(0x4302,src&255),(0x4303,(src>>8)&255),(0x4304,src>>16),(0x4305,n&255),(0x4306,n>>8),(0x420b,1)]:c.store(a,v)
 for i,f in enumerate(frames):
  if i:
   c.label('wait');c.absolute(0xad,0x6000);c.branch(0xf0,'wait')
  # Model delivery into inactive SNES WRAM, not MCU direct memory access.
  for off,b in f['staged']:
   c.store(0x2181,off&255);c.store(0x2182,off>>8);c.store(0x2183,1)
   src=0xc000+len(data);data.extend(b);dma(src,len(b),0x80,0)
  if i:blank('update');c.store(0x420c,0)
  for k,src,dst,n in f['commands']:
   assert 0x7f0000<=src<src+n<=0x800000
   if k==0:c.store(0x2116,(dst//2)&255);c.store(0x2117,dst>>9);port,mode=0x18,1
   elif k==1:c.store(0x2121,0);port,mode=0x22,2
   elif k==2:c.store(0x2102,0);c.store(0x2103,0);port,mode=4,0
   elif k==3:
    # Table is already resident. Read it directly from candidate bank7F;
    # no WRAM->WRAM DMA (invalid on SNES), and no CPU copy in vblank.
    assert src==0x7f6500+i*32768;continue
   else:raise AssertionError(k)
   dma(src,n,port,mode)
  if not i:blank('reveal')
  for port,val in [(0x210d,f['h']),(0x210e,f['v'])]:c.store(port,val&255);c.store(port,val>>8)
  # Switch this pointer on EVERY ACKed scene, including unchanged HDMA.
  for a,v in [(0x4310,3),(0x4311,0x0d),(0x4312,0),(0x4313,0x65+i*128),(0x4314,0x7f),(0x420c,2)]:c.store(a,v)
  if not i:c.store(0x2100,15)
  c.store(0x7000,i+1)
 c.label('done');c.branch(0x80,'done');code=c.finish()
 assert len(code)<0x4000 and len(data)<0x3fc0
 rom=bytearray([255])*32768;rom[:len(code)]=code;rom[0x4000:0x4000+len(data)]=data
 rom[0x7fc0:0x7fd5]=b'NES WRAM STAGE165'.ljust(21,b' ');rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 (out/'stage.sfc').write_bytes(rom)
 return dict(code_bytes=len(code),fixture_bytes=len(data))

def main():
 p=argparse.ArgumentParser()
 for n in ['video','out','gcc','arm-bin','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['video','out','gcc','arm_bin','mesen']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False)
 def run(exe,args,name,env=None):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=65,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')[-4000:]
 fw=ROOT/'src/nes/firmware'
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,fw/'nes_native_stage165.c',ROOT/'tests/nes-functional/native_stage165_host.c','-o','stage.exe'],'gcc')
 run(a.out/'stage.exe',[a.video/'frame12',a.video/'frame15'],'stage')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c',fw/'nes_native_stage165.c','-o','stage.o'],'arm')
 run(a.arm_bin/'arm-none-eabi-size.exe',['stage.o'],'arm-size')
 (a.out/'size_probe.c').write_text('#include "nes_native_stage165.h"\nchar stage_context_size[sizeof(struct nes_native_stage165)];\n')
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-mcpu=cortex-m4','-mthumb','-I',fw,'-c','size_probe.c','-o','size_probe.o'],'arm-layout')
 run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','--radix=d','size_probe.o'],'arm-layout-size')
 frames=[]
 for line in (a.out/'commands.tsv').read_text().splitlines():
  v=line.split();n=list(map(int,v[1:]))
  if v[0]=='H':i,serial,gen,payload,charged,count,h,vv=n;frames.append(dict(index=i,serial=serial,generation=gen,payload=payload,charged=charged,count=count,h=h,v=vv,commands=[]))
  else:frames[-1]['commands'].append(n)
 names=['bg','obj','map','cgram','oam','hdma'];offsets=[0,0x4000,0x5000,0x6000,0x6200,0x6500];inputs={}
 for i,f in enumerate(frames):
  assert f['count']==len(f['commands']);f['staged']=[];snap=(a.out/f'wram{i}.bin').read_bytes()
  for name,off in zip(names,offsets):
   path=a.video/f'frame{12+3*i}'/(name+'.bin');b=path.read_bytes();off+=i*32768
   assert snap[off:off+len(b)]==b;f['staged'].append((off,b));inputs[f'frame{12+3*i}/{name}.bin']=sha(path)
 assert [(f['payload'],f['count']) for f in frames]==[(5493,6),(18,2)]
 result=build(frames,a.out)
 (a.out/'capture.lua').write_text('local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_commands165.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 run(a.mesen,['--testRunner',a.out/'capture.lua',a.out/'stage.sfc','--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],'mesen',env)
 for i,f in enumerate(frames,1):
  gold=a.video/f'expected-{i}.rgb';assert (a.out/f'frame-{i}.rgb').read_bytes()==gold.read_bytes();inputs[gold.name]=sha(gold)
  f.pop('staged');f['rgb_sha256']=sha(a.out/f'frame-{i}.rgb')
 trace=[list(map(int,l.split())) for l in (a.out/'trace.tsv').read_text().splitlines()];commits=[l for l in trace if l[0]==0x7000];assert len(commits)==2 and 225<=commits[1][3]<262
 sources=['src/nes/firmware/nes_native_stage165.h','src/nes/firmware/nes_native_stage165.c','tests/nes-functional/native_stage165_host.c','tools/test_nes_native_stage165.py']
 result.update(passed=True,pixels=114688,frames=frames,commit_scanline=commits[1][3],inputs=inputs,public_sources={n:sha(ROOT/n) for n in sources},scope='C delta and ownership; modeled WRAM adapter; real SNES WRAM DMA/direct bank7F HDMA/PPU. No cartridge SRAM, actual MCU mailbox, physical bus, full link, FPGA fit or FPS proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
