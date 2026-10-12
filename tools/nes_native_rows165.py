# SPDX-License-Identifier: MIT
"""PC reference for sparse per-cell fine-Y changes in actual fetch events.

The old pinned consumer remains unchanged. Derived patterns copy only the rows
actually selected by the NES into SNES tile rows; allocation is transactional.
"""
from nes_native_commands165 import Consumer,Fetch,require,allocate

class RowConsumer:
 def __init__(self):self.consumer=Consumer();self.identities={}
 def prepare(self,words,rows,tiles,**limits):
  cells=[{} for _ in range(224)];sprites=[]
  for word in words:
   f=Fetch.unpack(word)
   if f.obj:sprites.append(f)
   else:
    require(f.x not in cells[f.row],'duplicate BG cell');cells[f.row][f.x]=f
  require(len(rows)==224 and all(set(c)==set(range(33)) for c in cells),'complete BG/raster rows required')
  groups=[];last=None;last_fine=None
  for y,c in enumerate(cells):
   fine=c[0].fine;signature=(tuple((c[x].tile,c[x].attr) for x in range(33)),tuple(rows[y][2]))
   if signature!=last or fine==0 or fine!=last_fine+1:groups.append([])
   groups[-1].append(y);last=signature;last_fine=fine
  require(len(groups)<=32,'BG row group capacity')
  identities={};identity=tuple(range(8));wanted={(f.tile,identity) for f in sprites}
  for group in groups:
   for x in range(33):
    mapping=list(identity);tag=cells[group[0]][x].tile
    for y in group:mapping[cells[y][0].fine]=cells[y][x].fine
    key=(tag,tuple(mapping));wanted.add(key)
    for y in group:identities[y,x]=key
  assigned=allocate(wanted,self.identities,8192)
  supplied={}
  for (tag,mapping),virtual in assigned.items():
   require(tag in tiles and len(tiles[tag])==16,'complete physical tile required')
   source=tiles[tag];supplied[virtual]=bytes(source[mapping[y]+p] for p in (0,8) for y in range(8))
  normalized=[]
  for y,c in enumerate(cells):
   for x,f in c.items():normalized.append(Fetch(assigned[identities[y,x]],c[0].fine,f.slot,y,x,f.attr,False,0).pack())
  for f in sprites:normalized.append(Fetch(assigned[f.tile,identity],f.fine,f.slot,f.row,f.x,f.attr,True,f.rank).pack())
  packet=self.consumer.prepare(normalized,rows,supplied,**limits)
  packet['physical_identities']=assigned
  packet['derived_patterns']=sum(mapping!=identity for tag,mapping in assigned)
  return packet
 def commit(self,packet):
  self.consumer.commit(packet);self.identities=packet['physical_identities']
