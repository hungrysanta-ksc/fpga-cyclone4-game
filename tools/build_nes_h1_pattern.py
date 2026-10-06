# SPDX-License-Identifier: MIT
# Original H1 maps, ROM producer image and actual 65816 MMIO/DMA diagnostic client.
from pathlib import Path
import argparse,hashlib,json,struct
from build_nes_visual_h0 import FONT,COLORS,atlas
from build_nes_trace_replay import Asm,Code
CANDIDATE='NES-H1-PATTERN-033'
FONT={**FONT,
 'K':['10001','10010','10100','11000','10100','10010','10001'],
 'W':['10001','10001','10001','10101','10101','10101','01010'],
 'M':['10001','11011','10101','10101','10001','10001','10001'],
 'P':['11110','10001','10001','11110','10000','10000','10000']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def scene(page):
 img=bytearray(256*224)
 def rect(x,y,w,h,c):
  for yy in range(y,y+h):img[yy*256+x:yy*256+x+w]=bytes([c])*w
 def text(s,y,c=1,scale=2):
  x=(256-(len(s)*6-1)*scale)//2
  for char in s:
   for dy,row in enumerate(FONT[char]):
    for dx,v in enumerate(row):
     if v=='1':rect(x+dx*scale,y+dy*scale,scale,scale,c)
   x+=6*scale
 rect(8,8,240,2,3);rect(8,214,240,2,3);rect(8,8,2,208,3);rect(246,8,2,208,3)
 text('NES H1 033',18)
 if page in (1,2,3):
  text(str(page)+' / '+['GRID','BARS','CROSS'][page-1],42,2)
  if page==1:
   for y in range(4):
    for x in range(8):rect(32+x*24,72+y*20,22,18,1 if (x+y)%2==0 else 3)
  elif page==2:
   for x in range(8):rect(32+x*24,72,22,78,1+x%3)
  else:
   rect(32,72,192,78,3);rect(38,78,180,66,0);rect(120,80,16,62,2);rect(52,102,152,16,1)
  text('LINK SCREEN '+str(page),166);text('AUTO CHANGE 1 SEC',192,3,1)
 elif page==0:
  text('LINK WAIT',72,2);text('NO FRAME',108);text('RESET IF ERROR',176,3,1)
 else:
  text('LINK ERROR',72,2);text('RESET',112);text('NO PASS',176,3,1)
 return bytes(img)
def build(out):
 assert not out.exists();out.mkdir(parents=True)
 tiles=[bytes(16)];lookup={tiles[0]:0};maps=[]
 for page in range(5):
  pixels=scene(page);raw=atlas(pixels);indices=[]
  for start in range(0,len(raw),16):
   tile=bytes(raw[start:start+16])
   if tile not in lookup:lookup[tile]=len(tiles);tiles.append(tile)
   indices.append(lookup[tile])
  data=b''.join(struct.pack('<H',i) for i in indices)+bytes(256)
  assert len(data)==2048
  maps.append(data);(out/f'page-{page}.bin').write_bytes(data)
  (out/f'expected-{page}.rgb').write_bytes(b''.join(bytes(COLORS[p]) for p in pixels))
 chrdata=b''.join(tiles);assert len(chrdata)<=16384
 pattern=b''.join(maps[1:4]);(out/'h1-pattern.hex').write_text(''.join(f'{b:02x}\n' for b in pattern))
 rom=bytearray([255])*65536
 rom[0x8000:0x8000+len(chrdata)]=chrdata
 rom[0x2000:0x2800]=maps[0];rom[0x2800:0x3000]=maps[4]
 rom[0x3000:0x3200]=struct.pack('<4H',0,0x7fff,0x03ff,0x7fe0)+bytes(504)
 c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10)
 for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2101,0),(0x2105,0),(0x2106,0),(0x2107,0),
  (0x2108,0),(0x2109,0),(0x210a,0),(0x210b,2),(0x210c,0),(0x212c,1),(0x212d,0),
  (0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,224),(0x2133,0),(0x2115,128),
  (0x1ff0,0),(0x1fe0,0),(0x1fe6,0),(0x1fe8,0),(0x1fd0,1),(0x1fd1,0)]:
  c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 for a,v in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3)]:c.store(a,v)
 def dma(bank,src,dst,size,palette=False):
  if palette:c.store(0x2121,0)
  else:c.store(0x2116,dst&255);c.store(0x2117,dst>>8)
  for a,v in [(0x4300,2 if palette else 1),(0x4301,34 if palette else 24),
   (0x4302,src&255),(0x4303,src>>8),(0x4304,bank),(0x4305,size&255),(0x4306,size>>8),(0x420b,1)]:c.store(a,v)
 def blank(label):
  c.label(label+'a');c.absolute(0xad,0x4212);c.branch(0x30,label+'a')
  c.label(label+'b');c.absolute(0xad,0x4212);c.branch(0x10,label+'b')
 def require(a,value,label,error):
  c.absolute(0xad,a);c.emit(0xc9,value);c.branch(0xf0,label)
  c.store(0x1fe8,error);c.jump('error');c.label(label)
 dma(0,0xb000,0,512,True);dma(1,0x8000,0x2000,len(chrdata));dma(0,0xa000,0,2048)
 blank('startup');c.store(0x2100,15);c.store(0x1ff0,165)
 c.label('next')
 c.store(0x6002,1);c.store(0x6003,0)
 for src,dst in [(0x1fd0,0x6004),(0x1fd1,0x6005)]:c.absolute(0xad,src);c.absolute(0x8d,dst)
 c.emit(0xa2,255,255) # X=bounded poll budget, unchanged by status reads.
 c.label('acquire');c.store(0x6000,1)
 c.label('poll');c.absolute(0xad,0x6000);c.emit(0x89,4);c.branch(0xf0,'notfault')
 c.store(0x1fe8,4);c.jump('error')
 c.label('notfault');c.emit(0x89,1);c.branch(0xd0,'got')
 c.emit(0xca);c.branch(0xd0,'budget');c.store(0x1fe8,1);c.jump('error')
 c.label('budget');c.emit(0x89,2);c.branch(0xd0,'poll');c.jump('acquire')
 c.label('got')
 require(0x6006,0,'lengthlo',2);require(0x6007,8,'lengthhi',2)
 require(0x6001,0,'cleanstage',4);require(0x600a,0,'cleanfront',4)
 blank('transfer');c.store(0x1fe6,1);dma(0x40,0x8000,0,2048)
 require(0x6008,0,'readlo',3);require(0x6009,8,'readhi',3)
 require(0x6001,0,'readstage',4);require(0x600a,0,'readfront',4)
 c.store(0x6000,2);c.emit(0xa2,255,255)
 c.label('commitwait');c.absolute(0xad,0x6000);c.branch(0xf0,'committed')
 c.emit(0x89,4);c.branch(0xd0,'commitfail');c.emit(0xca);c.branch(0xd0,'commitwait')
 c.label('commitfail');c.store(0x1fe8,5);c.jump('error')
 c.label('committed')
 # Visible page advances only after acknowledged commit; sequence never silently wraps.
 c.absolute(0xad,0x1fe0);c.emit(0x1a,0xc9,4);c.branch(0x90,'pageok');c.emit(0xa9,1)
 c.label('pageok');c.absolute(0x8d,0x1fe0);c.store(0x1fe6,3)
 c.emit(0xa0,59,0);c.label('hold');blank('holdframe');c.emit(0x88);c.branch(0xd0,'hold')
 c.emit(0xc2,0x20);c.absolute(0xad,0x1fd0);c.emit(0x1a);c.absolute(0x8d,0x1fd0)
 c.emit(0xe2,0x20);c.branch(0xd0,'again');c.store(0x1fe8,6);c.jump('error')
 c.label('again');c.jump('next')
 c.label('error');blank('errblank');dma(0,0xa800,0,2048)
 c.store(0x1fe0,4);c.store(0x1fe6,255);c.store(0x2100,15)
 c.label('stopped');c.jump('stopped')
 body=c.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
 boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
 boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
 boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
 rom[:len(boot.finish())]=boot.finish();rom[0x7fc0:0x7fd5]=b'NES H1 PATTERN 033'.ljust(21,b' ')
 rom[0x7fd5:0x7fdc]=bytes([0x20,0,6,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 (out/'nes-h1-pattern-033.sfc').write_bytes(rom)
 m={'candidate':CANDIDATE,'builder_sha256':sha(__file__),'rom_sha256':sha(out/'nes-h1-pattern-033.sfc'),
 'pattern_sha256':sha(out/'h1-pattern.hex'),'chr_bytes':len(chrdata),'body_bytes':len(body),
 'packet_bytes':2048,'page_order':[1,2,3],'hardware_eligible':False,
 'scope':'Original H1 diagnostic. Cold common reset epoch1 assumption; board loader/reset epoch handoff unresolved.'}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out)
