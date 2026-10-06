# Original readable SNES hardware diagnostic. SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,struct
from build_nes_trace_replay import Asm,Code
FONT={
' ':['00000']*7,
'0':['01110','10001','10011','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['01110','00100','00100','00100','00100','00100','01110'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'N':['10001','11001','11001','10101','10011','10011','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'/':['00001','00001','00010','00100','01000','10000','10000']}
COLORS=[(0,0,0),(255,255,255),(255,255,0),(0,255,255)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def scene(page):
 img=bytearray(256*224)
 def rect(x,y,w,h,c):
  assert 0<=x<x+w<=256 and 0<=y<y+h<=224
  for row in range(y,y+h):img[row*256+x:row*256+x+w]=bytes([c])*w
 def text(label,y,color=1,scale=2):
  x=(256-(len(label)*6-1)*scale)//2
  for char in label:
   for dy,line in enumerate(FONT[char]):
    for dx,bit in enumerate(line):
     if bit=='1':rect(x+dx*scale,y+dy*scale,scale,scale,color)
   x+=6*scale
 rect(8,8,240,2,3);rect(8,214,240,2,3);rect(8,8,2,208,3);rect(246,8,2,208,3)
 text('NES H0 030',18)
 names=['GRID','BARS','CROSS'];text(f'{page} / '+names[page-1],42,2)
 if page==1:
  for y in range(4):
   for x in range(8):rect(32+x*24,72+y*20,22,18,1 if (x+y)%2==0 else 3)
 elif page==2:
  for x in range(8):rect(32+x*24,72,22,78,1+x%3)
 else:
  rect(32,72,192,78,3);rect(38,78,180,66,0)
  rect(120,80,16,62,2);rect(52,102,152,16,1)
 text(f'SCREEN {page} OF 3',166)
 text('AUTO CHANGE 1 SEC',192,3,1)
 return bytes(img)
def atlas(pixels):
 out=bytearray()
 for ty in range(28):
  for tx in range(32):
   for y in range(8):
    v=pixels[(ty*8+y)*256+tx*8:(ty*8+y)*256+tx*8+8]
    out.extend([sum(((p>>bit)&1)<<(7-x) for x,p in enumerate(v)) for bit in (0,1)])
 assert len(out)==14336
 return out
def build(out):
 assert not out.exists();out.mkdir(parents=True)
 rom=bytearray([255])*131072
 for i in range(3):
  pixels=scene(i+1);rom[(i+1)*0x8000:(i+1)*0x8000+14336]=atlas(pixels)
  (out/f'expected-{i+1}.rgb').write_bytes(b''.join(bytes(COLORS[p]) for p in pixels))
 tilemap=b''.join(struct.pack('<H',i if i<896 else 0) for i in range(1024))
 rom[0x2000:0x2800]=tilemap
 rom[0x2800:0x2a00]=struct.pack('<4H',0,0x7fff,0x03ff,0x7fe0)+bytes(504)
 c=Code(0x7e2000);c.emit(0x78,0xe2,0x20,0xc2,0x10)
 for reg,value in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2101,0),(0x2105,0),(0x2106,0),
   (0x2107,0),(0x2108,0),(0x2109,0),(0x210a,0),(0x210b,2),(0x210c,0),
   (0x212c,1),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0),
   (0x2115,128),(0x1ff0,0),(0x1fe0,0),(0x1fe6,0)]:
  c.store(reg,value)
 for reg in range(0x2123,0x212c):c.store(reg,0)
 for reg,value in [(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,3)]:c.store(reg,value)
 def dma(bank,src,dst,size,palette=False):
  if palette:c.store(0x2121,0)
  else:c.store(0x2116,dst&255);c.store(0x2117,dst>>8)
  for reg,value in [(0x4300,2 if palette else 1),(0x4301,0x22 if palette else 0x18),
     (0x4302,src&255),(0x4303,src>>8),(0x4304,bank),(0x4305,size&255),(0x4306,size>>8),(0x420b,1)]:c.store(reg,value)
 dma(0,0xa800,0,512,True)
 for i in range(3):dma(i+1,0x8000,(i+1)*0x2000,14336)
 def blank(label):
  c.label(label+'_active');c.absolute(0xad,0x4212);c.branch(0x30,label+'_active')
  c.label(label+'_blank');c.absolute(0xad,0x4212);c.branch(0x10,label+'_blank')
 c.label('cycle')
 for i in range(3):
  blank('page'+str(i));c.store(0x1fe6,1)
  dma(0,0xa000,0,2048)
  c.store(0x210b,(i+1)*2);c.store(0x1fe0,i+1);c.store(0x2100,15);c.store(0x1ff0,165);c.store(0x1fe6,3)
  c.emit(0xa0,59,0) # 59 further boundaries; next page waits its own60th.
  c.label('delay'+str(i));blank('hold'+str(i))
  c.emit(0x88);c.branch(0xd0,'delay'+str(i))
 c.jump('cycle')
 body=c.finish();assert len(body)<4096;rom[0x1000:0x1000+len(body)]=body
 boot=Asm(0x8000);boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x20)
 boot.emit(0xa9);boot.word(len(body)-1);boot.emit(0xa2);boot.word(0x9000);boot.emit(0xa0);boot.word(0x2000)
 boot.emit(0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);boot.long(0x5c,0x7e2000)
 rom[:len(boot.finish())]=boot.finish()
 rom[0x7fc0:0x7fd5]=b'NES H0 VISUAL 030'.ljust(21,b' ')
 rom[0x7fd5:0x7fdc]=bytes([0x20,0,7,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
 for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
 checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
 assert len(rom)==131072
 (out/'nes-h0-visual-030.sfc').write_bytes(rom)
 m={'candidate':'NES-H0-VISUAL-030','rom_sha256':sha(out/'nes-h0-visual-030.sfc'),'builder_sha256':sha(__file__),'body_bytes':len(body),'display':[256,224],'page_hold_frames':60,'page_order':[1,2,3],'source':'Original readable SNES-only diagnostic; not a NES fetch replay','hardware_tested':False}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 print(json.dumps(m,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out)
