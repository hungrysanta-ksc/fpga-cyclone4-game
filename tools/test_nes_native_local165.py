# SPDX-License-Identifier: MIT
"""Real 65816 local comparison, dynamic DMA, pixels and rejection checks."""
from pathlib import Path
import argparse,json,struct,subprocess,os
from nes_game147 import ROOT,sha
from build_nes_trace_replay import Code
from nes_native_local165 import emit,emit_upload,call,OFFSETS

def build(video,out):
 c=Code(0x8000);data=bytearray();inputs={};lengths=[]
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
 for a,v in [(0x2100,128),(0x4200,1),(0x420c,0),(0x2105,0),(0x2106,0),(0x2107,0x41),(0x210b,0),(0x2101,1),(0x212c,0x11),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0),(0x2115,128),(0x1024,0),(0x1034,0)]:c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 # Initialize fixture-only padding before the later whole-slot MVN copies.
 # Overlap propagates one initialized zero; never reads undefined WRAM.
 c.emit(0xa9,0);c.long(0x8f,0x7f0000);c.emit(0xc2,0x20)
 c.emit(0xa9,0xfe,0xff,0xa2,0,0,0xa0,1,0,0x54,0x7f,0x7f)
 c.emit(0xe2,0x20,0xa9,0,0x48,0xab)
 def word(a,v):c.emit(0xa9);c.word(v);c.absolute(0x8d,a)
 def compare(case):
  c.emit(0xe2,0x20);c.store(0x7002,case);c.emit(0xc2,0x20);call(c,'local165_entry')
  c.emit(0xe2,0x20);c.store(0x7003,case);c.emit(0xc2,0x20)
 for i,frame in enumerate([12,15]):
  if i:
   c.label('wait_picture');c.absolute(0xad,0x6000);c.branch(0xf0,'wait_picture')
  lens=[]
  for name,offset in zip(['bg','obj','map','cgram','oam','hdma'],OFFSETS):
   p=video/f'frame{frame}'/(name+'.bin');b=p.read_bytes();lens.append(len(b));inputs[f'frame{frame}/{name}.bin']=sha(p)
   src=0xc000+len(data);data.extend(b);dest=offset+i*32768
   for a,v in [(0x2181,dest&255),(0x2182,dest>>8),(0x2183,1),(0x4300,0),(0x4301,0x80),(0x4302,src&255),(0x4303,src>>8),(0x4304,0),(0x4305,len(b)&255),(0x4306,len(b)>>8),(0x420b,1)]:c.store(a,v)
  lengths.append(lens);s=list(map(int,(video/f'frame{frame}/summary.txt').read_text().split()))
  c.emit(0xc2,0x20)
  for j,n in enumerate(lens):word(0x1000+j*2,n)
  for j,n in enumerate(lengths[0] if i else [0]*6):word(0x1010+j*2,n)
  for a,v in [(0x1020,i*32768),(0x1022,0),(0x102c,s[-2]),(0x102e,s[-1]),(0x1030,5000),(0x1036,0)]:word(a,v)
  compare(i+1);call(c,'upload165_entry');c.emit(0xe2,0x20);c.store(0x1024,1);c.store(0x7000,i+1)
 # Hold second picture until captured before destructively testing rejection.
 c.label('wait_second');c.absolute(0xad,0x6000);c.emit(0xc9,2);c.branch(0xd0,'wait_second');c.emit(0xc2,0x20)
 # Same data with reversed slots would not be a no-op; duplicate actual scene15
 # into old bank before no-op using CPU MVN (test fixture only).
 word(0x1022,0);word(0x1020,0x8000)
 c.emit(0xa9,0xff,0x7f,0xa2,0,0x80,0xa0,0,0,0x54,0x7f,0x7f)
 c.emit(0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20) # MVN sets DBR
 word(0x1020,0);word(0x1022,0x8000);compare(3)
 word(0x1020,0x8000);word(0x1022,0)
 # Metadata/range guard; uploader must perform no writes for rejected list.
 word(0x1020,1);compare(4);call(c,'upload165_entry');word(0x1020,0x8000)
 word(0x1000,16385);compare(5);word(0x1000,lengths[1][0])
 # Dirty words straddle a 64-byte boundary -> one six-byte VRAM command.
 c.emit(0xa9,1,0);c.long(0x8f,0x7fd03e);c.emit(0xa9,2,0);c.long(0x8f,0x7fd042);compare(6)
 word(0x1030,1);compare(7);call(c,'upload165_entry');word(0x1030,65535)
 # 34 separated changes exceed bounded command storage.
 for i in range(34):c.emit(0xa9,0xff,0xff);c.long(0x8f,0x7fd100+i*64)
 compare(8);call(c,'upload165_entry')
 # Odd final HDMA byte must be included in comparison.
 c.emit(0xa9,0xff,0x7f,0xa2,0,0x80,0xa0,0,0,0x54,0x7f,0x7f)
 c.emit(0xe2,0x20,0xa9,0,0x48,0xab);c.emit(0xa9,1);c.long(0x8f,0x7fe500+lengths[1][5]-1);c.emit(0xc2,0x20)
 word(0x1030,5000);compare(9)
 c.emit(0xe2,0x20);c.store(0x7004,0xa5);c.label('halt');c.branch(0x80,'halt')
 meta=emit(c,service='service');upload=emit_upload(c)
 # Cooperative pad polling; production caller also services receive/exit.
 c.label('service');c.absolute(0xee,0x1036);c.emit(0x08,0xe2,0x20);c.absolute(0xad,0x4212);c.branch(0x30,'service_blank')
 c.store(0x1034,0);c.branch(0x80,'service_done')
 c.label('service_blank');c.emit(0x89,1);c.branch(0xd0,'service_done');c.absolute(0xad,0x1034);c.branch(0xd0,'service_done')
 c.absolute(0xad,0x4218);c.absolute(0x8d,0x6002);c.absolute(0xad,0x4219);c.absolute(0x8d,0x6003);c.store(0x1034,1)
 c.label('service_done');c.emit(0x28,0x60)
 code=c.finish();assert len(code)<0x4000 and len(data)<0x3fc0
 rom=bytearray([255])*32768;rom[:len(code)]=code;rom[0x4000:0x4000+len(data)]=data
 rom[0x7fc0:0x7fd5]=b'NES LOCAL DIFF165'.ljust(21,b' ');rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 (out/'local.sfc').write_bytes(rom);return dict(local=meta,upload=upload,test_rom_bytes=len(code),inputs=inputs)

def main():
 p=argparse.ArgumentParser()
 for n in ['video','stage','out','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in ['video','stage','out','mesen']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False);r=build(a.video,a.out)
 (a.out/'capture.lua').write_text('local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_local165.lua').read_text())
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'mesen.log').open('wb') as f:
  process=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'local.sfc'),'--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert process.returncode==0,(a.out/'mesen.log').read_text(errors='replace')[-4000:]
 cases=json.loads((a.out/'cases.json').read_text());assert len(cases)==9
 old=json.loads((a.stage/'result.json').read_bytes())
 for i in range(2):
  q=cases[i];assert q['status']==2 and q['payload']==old['frames'][i]['payload'] and q['charged']==old['frames'][i]['charged']
  expected=[[src&65535,dest,size,kind] for kind,src,dest,size in old['frames'][i]['commands']];assert q['commands']==expected,(q,expected)
  assert (a.out/f'frame-{i+1}.rgb').read_bytes()==(a.video/f'expected-{i+1}.rgb').read_bytes()
 assert cases[2]['status']==2 and cases[2]['count']==0
 assert [cases[i]['status'] for i in [3,4,6,7]]==[0xe1,0xe1,0xe3,0xe2]
 assert cases[5]['commands']==[[0xd03e,0x803e,6,0]],cases[5]
 assert cases[8]['commands']==[[0xe500,0,21,3]],cases[8]
 sources=['tools/nes_native_local165.py','tools/test_nes_native_local165.py','snes/video_probe/capture_native_local165.lua']
 r.update(passed=True,cases=cases,pixels=114688,public_sources={n:sha(ROOT/n) for n in sources},stage_result_sha256=sha(a.stage/'result.json'),scope='Actual65816 WRAM local comparison and dynamic PPU DMA, sealed game fixtures. No MCU mailbox, physical board ACK, whole link/fit or gameplay FPS.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
