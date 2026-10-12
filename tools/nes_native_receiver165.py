# SPDX-License-Identifier: MIT
"""PC reference for the bounded host record contract; not MCU firmware.

Transport receipt is separate from PREPARED and COMMIT. The caller may only
publish a returned committed snapshot, and must reset this receiver whenever
the common transport reset is asserted.
"""
class Receiver:
 def __init__(self):self.reset()
 def reset(self):
  self.state='idle';self.generation=None;self.tables=[{} for _ in range(6)];self.tiles={};self.kinds={};self.records=0;self.bytes=0;self.last_tile=-1;self.lane=0
 def require(self,condition,why):
  if not condition:self.state='failed';raise ValueError(why)
 def prepared(self,accept=True):
  self.require(self.state=='complete','only a complete scene may be prepared')
  self.state='prepared' if accept else 'rejected';return self.generation,accept
 def feed(self,word):
  self.require(isinstance(word,int) and 0<=word<1<<96,'record width')
  kind=word>>93;generation=word>>77&65535;index=word>>64&8191;value=word&((1<<64)-1)
  if kind==7 and index==2:
   self.require(self.generation is None or generation==self.generation,'ABORT generation')
   self.reset();return None
  if kind==7 and index==0:
   self.require(self.state=='idle','overlapping scene')
   self.require(value>>48==0x1651 and value&4095==0,'header version/reserved')
   groups=value>>42&63;palettes=value>>36&63;rows=value>>28&255;objects=value>>20&255;exceptions=value>>12&255
   self.require(1<=groups<=32 and 1<=palettes<=2 and rows==224 and objects<=128 and exceptions<=128,'header limits')
   self.generation=generation;self.counts=[groups*33,224,objects,exceptions,224,palettes*32]
   self.geometry=(groups,objects,exceptions);self.next_kind=0;self.state='receiving';return None
  self.require(generation==self.generation,'record generation')
  if kind==7 and index==3:
   self.require(self.state=='prepared' and value==0,'unprepared COMMIT')
   snapshot=dict(generation=generation,tables=self.tables,tiles={t:bytes(b) for t,b in self.tiles.items()},kinds=self.kinds,geometry=self.geometry,records=self.records,bytes=self.bytes)
   self.reset();return snapshot
  if kind==7 and index==1:
   self.require(self.state=='receiving' and value>>32==0,'END state/reserved')
   self.require(all(len(t)==n for t,n in zip(self.tables,self.counts)),'incomplete geometry')
   self.require(value>>16==self.records and value&65535==self.bytes and self.lane==0,'END counts/partial tile')
   needed={}
   for cell in self.tables[0].values():needed[cell&8191]=needed.get(cell&8191,0)|1
   for obj in self.tables[2].values():needed[obj&8191]=needed.get(obj&8191,0)|2
   self.require(all(t in self.tiles and self.kinds[t]&k==k for t,k in needed.items()),'missing required CHR')
   self.state='complete';return None
  self.require(self.state=='receiving' and kind<7,'data outside receiving')
  if kind<6:
   while self.next_kind<6 and len(self.tables[self.next_kind])==self.counts[self.next_kind]:self.next_kind+=1
   self.require(kind==self.next_kind and index==len(self.tables[kind]),'table order/index')
   widths=[15,8,49,20,49,6]
   self.require(value<1<<widths[kind],'table reserved bits')
   self.tables[kind][index]=value
  else:
   self.require(all(len(t)==n for t,n in zip(self.tables,self.counts)),'CHR before geometry')
   lane=value>>8&15;k=value>>12&3
   self.require(value>>14==0 and k!=0 and lane==self.lane,'CHR reserved/lane')
   if lane==0:
    self.require(index>self.last_tile and len(self.tiles)<512,'CHR order/capacity')
    self.last_tile=index;self.tiles[index]=bytearray();self.kinds[index]=k
   self.require(index==self.last_tile and self.kinds[index]==k,'CHR tile identity')
   self.tiles[index].append(value&255);self.lane=(lane+1)%16;self.bytes+=1
  self.records+=1
