# SPDX-License-Identifier: MIT
"""Decode bounded producer RAM for PC verification, never a hardware raw buffer."""
from nes_native_commands165 import Fetch,require

def decode(path):
 lines=path.read_text().splitlines();h=lines[0].split();assert h[0]=='H'
 valid,error,rows,groups,objects,exceptions=int(h[1]),int(h[2],16),*map(int,h[3:])
 info=dict(valid=bool(valid),error=error,rows=rows,groups=groups,objects=objects,
           exceptions=exceptions,packet_bytes=groups*33*2+rows+objects*8+exceptions*3)
 if not valid:return info,[]
 maps={};raster={};sprites={};patches={}
 for line in lines[1:]:
  kind,address,value=line.split();kind=int(kind);address=int(address);value=int(value,16)
  target=[maps,raster,sprites,patches][kind];assert address not in target;target[address]=value
 assert len(maps)==groups*33 and len(raster)==rows==224 and len(sprites)==objects
 assert len(patches)==exceptions
 overrides={((v>>9)&255,(v>>3)&63):v&7 for v in patches.values()};assert len(overrides)==exceptions
 words=[]
 for y in range(224):
  g=raster[y]>>3;fine=raster[y]&7;assert g<groups
  for x in range(33):
   cell=maps[g*33+x];assert cell<1<<15
   words.append(Fetch(cell&8191,overrides.get((y,x),fine),0,y,x,cell>>13,False,0).pack())
 for value in sprites.values():
  require(value<1<<49,'compact reserved bits')
  tile=value&8191;top=(value>>13)&511;top=top-512 if top&256 else top
  x=(value>>22)&255;attr=(value>>30)&255;mask=(value>>38)&255;rank=(value>>46)&7
  for fine in range(8):
   if mask>>fine&1:
    y=top+(7-fine if attr&128 else fine);require(0<=y<224,'compact sprite row')
    words.append(Fetch(tile,fine,0,y,x,attr,True,rank).pack())
 return info,words

def equivalent(a,b):
 # Logical slots are not needed after physical tags have been resolved.
 keep=((1<<64)-1)^(511<<16)
 return sorted(w&keep for w in a)==sorted(w&keep for w in b)
