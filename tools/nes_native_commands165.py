# SPDX-License-Identifier: MIT
"""Bounded executable reference consumer of the fetch165 stream.

This runs on the development PC, not yet on the FPGA/MCU. It emits actual SNES
VRAM/OAM/CGRAM/HDMA bytes; unsupported scenes fail without changing the display
state. No ROM service requests or unbounded hardware work are implied.
"""
from dataclasses import dataclass
import struct
from build_nes_game164 import palette as nes_palette

class Unsupported(ValueError): pass
def require(ok,why):
 if not ok:raise Unsupported(why)

@dataclass(frozen=True)
class Fetch:
 tile:int; fine:int; slot:int; row:int; x:int; attr:int; obj:bool; rank:int
 @classmethod
 def unpack(cls,v):
  require(isinstance(v,int) and 0<=v<1<<53,'reserved descriptor bits')
  f=cls(v&8191,(v>>13)&7,(v>>16)&511,(v>>25)&255,(v>>33)&255,(v>>41)&255,bool((v>>49)&1),(v>>50)&7)
  require(f.row<224 and (f.obj or (f.x<=32 and f.attr<4 and f.rank==0)),'descriptor geometry')
  return f
 def pack(self):
  return self.tile|self.fine<<13|self.slot<<16|self.row<<25|self.x<<33|self.attr<<41|int(self.obj)<<49|self.rank<<50

@dataclass(frozen=True)
class Write:
 kind:str; address:int; data:bytes

def hdma(rows):
 """Mode3 direct HDMA: two writes HOFS then two VOFS, hold equal runs."""
 out=bytearray();i=0
 while i<len(rows):
  end=i+1
  while end<len(rows) and rows[end]==rows[i] and end-i<127:end+=1
  out.append(end-i);out+=struct.pack('<HH',*rows[i]);i=end
 return bytes(out+b'\0')

def allocate(wanted,old,capacity,start=0):
 require(len(wanted)<=capacity-start,'pattern working set capacity')
 kept={k:v for k,v in old.items() if k in wanted}
 used=set(kept.values());free=iter(i for i in range(start,capacity) if i not in used)
 for k in sorted(wanted):
  if k not in kept:kept[k]=next(free)
 return kept

def convert(source,mask=255,obj=False):
 require(len(source)==16,'missing complete physical tile')
 b=bytes(source[y+p] if (mask>>y)&1 else 0 for y in range(8) for p in (0,8))
 return b+bytes(16) if obj else b

class Consumer:
 """Copy-on-admission transaction; only commit an ACKed upload in live use."""
 def __init__(self):
  self.bg={};self.obj={};self.vram=bytes(65536);self.cgram=bytes(512)
  self.oam=bytes(544);self.scroll=b'';self.initial=True;self.serial=0

 def prepare(self,words,row_state,tiles,budget=5000,max_commands=32):
  require(len(row_state)==224,'224 row states required')
  require(len(words)<=9184,'raw event bound')
  fs=[Fetch.unpack(w) for w in words];bg=[{} for _ in range(224)];sprites=[[] for _ in range(224)]
  palettes=[];epochs=[]
  for fine_x,mask,pal in row_state:
   require(0<=fine_x<8 and mask==0x1e,'reference requires both layers, left edge on, no emphasis/grayscale')
   require(len(pal)==32 and all(0<=c<64 for c in pal),'palette shape')
   pal=tuple(pal)
   if pal not in palettes:palettes.append(pal)
   epochs.append(palettes.index(pal))
  require(len(palettes)<=2,'at most two palette epochs in resident CGRAM')
  require(all(p[0]==palettes[0][0] for p in palettes),'backdrop change needs CGRAM raster support')
  for f in fs:
   if f.obj:sprites[f.row].append(f)
   else:
    require(f.x not in bg[f.row],'duplicate BG cell');bg[f.row][f.x]=f
  require(all(set(r)==set(range(33)) for r in bg),'incomplete BG row')
  groups=[];scroll=[];last=None;lastfine=None
  for y,cells in enumerate(bg):
   fine=cells[0].fine;require(all(f.fine==fine for f in cells.values()),'different fine Y within BG row')
   signature=tuple((cells[x].tile,epochs[y]*4+cells[x].attr) for x in range(33))
   if signature!=last or fine==0 or fine!=lastfine+1:
    groups.append(signature);require(len(groups)<=32,'BG row group capacity')
   # SNES scanline0 is hidden; visible output y reads y+1+VOFS.
   scroll.append((row_state[y][0],((len(groups)-1)*8+fine-y-1)&1023))
   last=signature;lastfine=fine
  bgmap=allocate({tag for g in groups for tag,pal in g},self.bg,1024,1)
  fragments={};row_keys=[]
  for y,seq in enumerate(sprites):
   require(len(seq)<=8 and len({f.rank for f in seq})==len(seq),'sprite row/rank capacity')
   keys=[]
   for f in sorted(seq,key=lambda f:f.rank):
    top=y-(7-f.fine if f.attr&128 else f.fine)
    key=(f.x,top,f.tile,f.attr,epochs[y])
    # Preserve actual evaluated row coverage, not all primary-OAM rows.
    fragments[key]=fragments.get(key,0)|(1<<f.fine)
    if key not in keys:keys.append(key)
   row_keys.append(keys)
  require(len(fragments)<=128,'SNES OAM fragment capacity')
  edges={k:set() for k in fragments};degree={k:0 for k in fragments}
  for keys in row_keys:
   for a,b in zip(keys,keys[1:]):
    if b not in edges[a]:edges[a].add(b);degree[b]+=1
  order=[];ready=sorted(k for k,d in degree.items() if d==0)
  while ready:
   k=ready.pop(0);order.append(k)
   for b in sorted(edges[k]):
    degree[b]-=1
    if degree[b]==0:ready.append(b);ready.sort()
  require(len(order)==len(fragments),'inconsistent sprite priority order')
  # SNES also evaluates transparent OAM rows; masking alone does not avoid
  # its 32-object/34-sliver limit. All emitted objects are small 8x8.
  for y in range(224):
   require(sum(top<=y<top+8 for x,top,t,a,e in order)<=32,'SNES scanline object capacity')
  objmap=allocate({(k[2],fragments[k]) for k in order},self.obj,512)
  regions={0:bytes(16)}
  for tag,slot in bgmap.items():
   require(tag in tiles,'physical BG tile missing');regions[slot*16]=convert(tiles[tag])
  for (tag,mask),slot in objmap.items():
   require(tag in tiles,'physical OBJ tile missing');regions[0x4000+slot*32]=convert(tiles[tag],mask,True)
  tilemap=bytearray(4096)
  for y,g in enumerate(groups):
   for x,(tag,pal) in enumerate(g):
    at=((x//32)*1024+y*32+x%32)*2
    struct.pack_into('<H',tilemap,at,bgmap[tag]|pal<<10|0x2000)
  regions[0x8000]=bytes(tilemap)
  oam=bytearray(bytes([0,240,0,0])*128+bytes(32))
  for i,k in enumerate(order):
   x,top,tag,attr,epoch=k;slot=objmap[tag,fragments[k]]
   priority=2 if attr&32 else 3
   oam[i*4:i*4+4]=bytes([x,top&255,slot&255,(slot>>8)|((epoch*4+(attr&3))<<1)|(priority<<4)|(attr&0xc0)])
  colors=nes_palette();cgram=bytearray(512)
  cgram[:2]=colors[palettes[0][0]*2:palettes[0][0]*2+2]
  for epoch,pal in enumerate(palettes):
   for p in range(4):
    for c in range(4):
     for source,destination in [(p*4+c,(epoch*16+p*4+c)*2),(16+p*4+c,(128+epoch*64+p*16+c)*2)]:
      color=pal[source];cgram[destination:destination+2]=colors[color*2:color*2+2]
  table=hdma(scroll);memory=bytearray(self.vram);needed=set()
  for address,data in regions.items():
   require(address%2==0 and len(data)%2==0,'VRAM word alignment')
   memory[address:address+len(data)]=data
   for p in range(address,address+len(data),2):
    if self.initial or memory[p:p+2]!=self.vram[p:p+2]:needed.add(p)
  # Coalesce small unchanged gaps: DMA setup is more expensive than a few
  # bytes. Never include a gap across separate pattern/map regions >32 bytes.
  runs=[]
  for p in sorted(needed):
   if runs and p-runs[-1][1]<=32:runs[-1][1]=p+2
   else:runs.append([p,p+2])
  writes=[Write('vram',a,bytes(memory[a:b])) for a,b in runs]
  if self.initial or cgram!=self.cgram:writes.append(Write('cgram',0,bytes(cgram)))
  if self.initial or oam!=self.oam:writes.append(Write('oam',0,bytes(oam)))
  if self.initial or table!=self.scroll:writes.append(Write('hdma',0x9000,table))
  payload=sum(len(w.data) for w in writes);charged=payload+96*len(writes)
  require(self.initial or (charged<=budget and len(writes)<=max_commands),'vblank transaction budget')
  return dict(serial=self.serial,bg=bgmap,obj=objmap,vram=bytes(memory),cgram=bytes(cgram),oam=bytes(oam),
   scroll=table,scroll_rows=scroll,writes=writes,payload=payload,charged=charged,groups=len(groups),
   fragments=len(order),raw_events=len(fs),initial=self.initial)

 def commit(self,p):
  require(p['serial']==self.serial,'stale or duplicate commit')
  for n in ['bg','obj','vram','cgram','oam','scroll']:setattr(self,n,p[n])
  self.serial+=1;self.initial=False

def reference_rgb(words,rows,tiles):
 """Direct NES event pixels, independent of SNES slot/map/OAM/HDMA packing."""
 bg=[{} for _ in range(224)];obj=[[] for _ in range(224)]
 for w in words:
  f=Fetch.unpack(w)
  if f.obj:obj[f.row].append(f)
  else:bg[f.row][f.x]=f
 colors=struct.unpack('<64H',nes_palette());image=bytearray(256*224*3)
 def pixel(f,x):
  b=tiles[f.tile];bit=x if f.obj and f.attr&64 else 7-x
  return ((b[f.fine]>>bit)&1)|(((b[f.fine+8]>>bit)&1)<<1)
 for y in range(224):
  fine,mask,pal=rows[y]
  for x in range(256):
   b=bg[y][(x+fine)//8];v=pixel(b,(x+fine)%8);c=pal[b.attr*4+v] if v else pal[0]
   for f in sorted(obj[y],key=lambda f:f.rank):
    if f.x<=x<f.x+8:
     s=pixel(f,x-f.x)
     if s:
      if not(v and f.attr&32):c=pal[16+(f.attr&3)*4+s]
      break
   color=colors[c];rgb=bytes((((color>>shift)&31)<<3)|(((color>>shift)&31)>>2) for shift in [0,5,10])
   image[(y*256+x)*3:(y*256+x+1)*3]=rgb
 return bytes(image)
