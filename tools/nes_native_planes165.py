"""SPDX-License-Identifier: MIT
Bounded same-tile mixed-plane descriptors and PC reference consumer.

Only BG low/high fine-Y differences are represented. The original physical
tile remains required; virtual derived patterns are never PSRAM addresses.
"""
from nes_native_commands165 import Consumer,Fetch,require,allocate,reference_rgb

BASE=(1<<53)-1
MIXED=1<<56

def unpack(word):
 require(isinstance(word,int) and 0<=word<1<<57,'plane descriptor reserved bits')
 f=Fetch.unpack(word&BASE);low=(word>>53)&7
 if word&MIXED:require(not f.obj and low!=f.fine,'canonical BG plane exception')
 else:require(low==0,'unflagged plane exception');low=f.fine
 return f,low

def pack(f,low):
 require(0<=low<8 and (not f.obj or low==f.fine),'unsupported mixed OBJ')
 return f.pack()|((MIXED|low<<53) if low!=f.fine else 0)

def decode(path):
 lines=path.read_text().splitlines();h=lines[0].split();assert h[0]=='H'
 valid,error,rows,groups,objects,exceptions=int(h[1]),int(h[2],16),*map(int,h[3:])
 info=dict(valid=bool(valid),error=error,rows=rows,groups=groups,objects=objects,
  exceptions=exceptions,packet_bytes=groups*33*2+rows+objects*8+exceptions*3)
 if not valid:return info,[]
 tables=[{} for _ in range(4)]
 for line in lines[1:]:
  kind,address,value=line.split();kind=int(kind);address=int(address);value=int(value,16)
  assert address not in tables[kind];tables[kind][address]=value
 maps,raster,sprites,patches=tables
 assert len(maps)==groups*33 and len(raster)==rows==224 and len(sprites)==objects and len(patches)==exceptions
 overrides={}
 for v in patches.values():
  assert v<1<<20;y=(v>>12)&255;x=(v>>6)&63;hi=(v>>3)&7;lo=v&7
  assert y<224 and x<=32 and (y,x) not in overrides;overrides[y,x]=(hi,lo)
 words=[]
 for y in range(224):
  g=raster[y]>>3;fine=raster[y]&7;assert g<groups
  for x in range(33):
   cell=maps[g*33+x];assert cell<1<<15
   hi,lo=overrides.get((y,x),(fine,fine))
   words.append(pack(Fetch(cell&8191,hi,0,y,x,cell>>13,False,0),lo))
 for value in sprites.values():
  require(value<1<<49,'compact reserved bits')
  tile=value&8191;top=(value>>13)&511;top=top-512 if top&256 else top
  x=(value>>22)&255;attr=(value>>30)&255;mask=(value>>38)&255;rank=(value>>46)&7
  for fine in range(8):
   if mask>>fine&1:
    y=top+(7-fine if attr&128 else fine);require(0<=y<224,'compact sprite row')
    words.append(Fetch(tile,fine,0,y,x,attr,True,rank).pack())
 return info,words

class PlaneConsumer:
 def __init__(self):self.consumer=Consumer();self.identities={}
 def prepare(self,words,rows,tiles,**limits):
  cells=[{} for _ in range(224)];sprites=[]
  for word in words:
   f,lo=unpack(word)
   if f.obj:sprites.append(f)
   else:require(f.x not in cells[f.row],'duplicate BG cell');cells[f.row][f.x]=(f,lo)
  require(len(rows)==224 and all(set(c)==set(range(33)) for c in cells),'complete BG/raster rows required')
  groups=[];last=None;last_fine=None
  for y,c in enumerate(cells):
   fine=c[0][0].fine;signature=(tuple((c[x][0].tile,c[x][0].attr) for x in range(33)),tuple(rows[y][2]))
   if signature!=last or fine==0 or fine!=last_fine+1:groups.append([])
   groups[-1].append(y);last=signature;last_fine=fine
  require(len(groups)<=32,'BG row group capacity')
  identities={};identity=tuple(range(16));wanted={(f.tile,identity) for f in sprites}
  for group in groups:
   for x in range(33):
    mapping=list(identity);tag=cells[group[0]][x][0].tile
    for y in group:
     dest=cells[y][0][0].fine;f,lo=cells[y][x];mapping[dest]=lo;mapping[dest+8]=f.fine+8
    key=(tag,tuple(mapping));wanted.add(key)
    for y in group:identities[y,x]=key
  assigned=allocate(wanted,self.identities,8192);supplied={}
  for (tag,mapping),virtual in assigned.items():
   require(tag in tiles and len(tiles[tag])==16,'complete physical tile required')
   supplied[virtual]=bytes(tiles[tag][source] for source in mapping)
  normalized=[]
  for y,c in enumerate(cells):
   for x,(f,lo) in c.items():normalized.append(Fetch(assigned[identities[y,x]],c[0][0].fine,f.slot,y,x,f.attr,False,0).pack())
  for f in sprites:normalized.append(Fetch(assigned[f.tile,identity],f.fine,f.slot,f.row,f.x,f.attr,True,f.rank).pack())
  packet=self.consumer.prepare(normalized,rows,supplied,**limits)
  packet['physical_identities']=assigned;packet['derived_patterns']=sum(mapping!=identity for tag,mapping in assigned)
  return packet
 def commit(self,packet):self.consumer.commit(packet);self.identities=packet['physical_identities']

def reference_planes_rgb(words,rows,tiles):
 """Independent per-cell plane-byte substitution, without consumer grouping."""
 supplied=dict(tiles);normalized=[];next_virtual=8191
 # Reference Fetch has 13-bit tags. Reassign only used originals to dense IDs.
 originals=sorted({unpack(w)[0].tile for w in words});tags={t:i for i,t in enumerate(originals)}
 supplied={tags[t]:tiles[t] for t in originals};next_virtual=len(tags)
 mixed={}
 for word in words:
  f,lo=unpack(word);tag=tags[f.tile]
  if lo!=f.fine:
   key=f.tile,lo,f.fine
   if key not in mixed:
    require(next_virtual<8192,'reference pattern capacity');mixed[key]=next_virtual;next_virtual+=1
    value=bytearray(tiles[f.tile]);value[f.fine]=value[lo];supplied[mixed[key]]=bytes(value)
   tag=mixed[key]
  normalized.append(Fetch(tag,f.fine,f.slot,f.row,f.x,f.attr,f.obj,f.rank).pack())
 return reference_rgb(normalized,rows,supplied)
