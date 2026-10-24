# SPDX-License-Identifier: MIT
"""Native expanded staging DMA; independent original compressed byte oracle."""
import inspect,struct
import probe_nes_ordinary268 as base
from build_nes_trace_replay import Code
from nes_delta231 import once

def rom(d,mode):
 c=Code(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a in (0x50,0x51,0x4200,0x420c):c.store(a,0)
 c.store(0x2100,0x80)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 def stop():lda(0x6001);cond(0xd0,'stop')
 c.label('next');stop();lda(0x6000);cond(0xf0,'next')
 for i in range(9):lda(0x6060+i);sta(0x30+i)
 for i in range(4):lda(0x6048+i);sta(0x60+i)
 c.label('execute');stop();lda(0x30);cond(0xd0,'zero')
 # Any write into [bank:6515,6961) invalidates the reusable zero tail.
 lda(0x31);c.emit(0xc9,5);cond(0xd0,'copy')
 c.emit(0xc2,0x20);lda(0x32);c.emit(0x29,0xff,0x7f,0xc9,0x61,0x69);cond(0xb0,'copy16')
 lda(0x32);c.emit(0x29,0xff,0x7f,0x18);c.absolute(0x6d,0x34);c.emit(0xc9,0x16,0x65);cond(0x90,'copy16')
 c.emit(0xe2,0x20);lda(0x38);c.emit(0xc2,0x20,0x29,0xff,0,0xaa,0xe2,0x20,0xa9,0);c.absolute(0x9d,0x50)
 c.jump('copy')
 c.label('copy16');c.emit(0xe2,0x20)
 c.label('copy');c.emit(0xc2,0x20);lda(0x32);sta(0x2181);lda(0x34);sta(0x4305);c.emit(0xe2,0x20)
 for a,v in [(0x2183,1),(0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
 c.jump('dma_setup')
 c.label('zero')
 # Retain real two-byte seed reads and STOP-aware bank cache, not fake reads.
 c.emit(0xaf,0,8,0x40);cond(0xd0,'stop');c.emit(0xaf,1,8,0x40);cond(0xd0,'stop')
 lda(0x38);c.emit(0xc2,0x20,0x29,0xff,0,0xaa,0xe2,0x20)
 if mode=='reuse':c.absolute(0xbd,0x50);cond(0xd0,'ack')
 c.label('zero_dma');stop();c.emit(0xc2,0x20);lda(0x32);sta(0x2181);c.emit(0xa9,0x4c,4);sta(0x4305);c.emit(0xe2,0x20)
 fixes={}
 for a,v in [(0x2183,1),(0x4300,8),(0x4301,0x80),(0x4302,0),(0x4303,0),(0x4304,0),(0x420b,1)]:
  if a in (0x4302,0x4303):fixes[a]=len(c.data)+1
  c.store(a,v)
 c.label('zero_done');c.emit(0xa9,1);c.absolute(0x9d,0x50);c.jump('ack')
 c.label('dma_setup');stop();lda(0x31);c.emit(0xc9,5);cond(0xf0,'ack')
 c.emit(0xc2,0x20);lda(0x32);sta(0x4302);lda(0x34);sta(0x4305);c.emit(0xe2,0x20);c.store(0x4304,0x7f)
 lda(0x31);c.emit(0xc9,3);cond(0xd0,'oam')
 lda(0x36);sta(0x2121);c.store(0x4300,2);c.store(0x4301,0x22);c.jump('dma')
 c.label('oam');lda(0x36);sta(0x2102);lda(0x37);sta(0x2103);c.store(0x4300,0);c.store(0x4301,4)
 c.label('dma');stop();c.store(0x420b,1)
 c.label('ack');stop()
 for i in range(4):lda(0x60+i);sta(0x604c+i)
 c.store(0x6059,0xa5);c.jump('next')
 c.label('stop');c.store(0x50,0);c.store(0x51,0);c.store(0x6006,0xa5);c.jump('next')
 body=bytearray(c.finish());zero=0x8000+len(body);c.labels['zero_source']=zero
 body[fixes[0x4302]]=zero&255;body[fixes[0x4303]]=zero>>8
 r=bytearray([255])*32768;r[:len(body)]=body;r[len(body)]=0
 r[0x7fc0:0x7fd5]=b'NES325 NATIVE DMA    ';r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for i in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,i,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum)
 (d/'ordinary.sfc').write_bytes(r);return len(body),c.labels

def main():
 lua=base.LUA
 a=lua.index('emu.addMemoryCallback(function(a,v)if a==0x6000');b=lua.index('emu.addMemoryCallback(function()execute=',a)
 lua=lua[:a]+'''local descriptor_reads=0
local function special()return p(0)==5 and p(1)==5 and word(10)==21 and word(14)==1100 and word(12)==2 and p(16)==0 and p(17)==0 end
local function expanded()return p(0)==2 and word(12) or word(14)end
local function staged()return special() and 2 or expanded()end
emu.addMemoryCallback(function(a,v)
 if a==0x6001 then return event(0,a,0)end
 if a==0x6000 then return event(0,a,1)end
 if a>=0x6048 and a<=0x604b then return event(0,a,math.floor(at/2^(8*(a-0x6048)))%256)end
 local i=a-0x6060;assert(i==descriptor_reads,'native descriptor read order');descriptor_reads=descriptor_reads+1;first=first or clock()
 local bank=(word(4)-1)%2
 local target=(p(1)==3 and 0x6000 or p(1)==4 and 0x6200 or 0x6500)+bank*0x8000+word(10)
 local pp=math.floor(word(10)/2);local n=staged()
 local desc={special() and 1 or 0,p(1),target%256,math.floor(target/256),n%256,math.floor(n/256),pp%256,math.floor(pp/256),bank}
 return event(0,a,desc[i+1])
end,emu.callbackType.read,0x6000,0x6068)
emu.addMemoryCallback(function(a,v)
 local i=a-0x400800;assert(i==reads,'expanded staging order');lastread=clock();reads=reads+1
 return event(0,a,p(16+i%word(12)))
end,emu.callbackType.read,0x400800,0x4017ff)
'''+lua[b:]
 a=lua.index(' if a~=0x601c');b=lua.index(' local count=p(0)',a)
 lua=lua[:a]+''' if a~=0x6059 then ack[a-0x604c]=v;return end
 if zero_live then assert(zero_reads==1100 and zero_writes==1100,'zero DMA count');zero_live=false;zero_bytes=zero_bytes+zero_writes end
 assert(v==0xa5 and reads==staged() and descriptor_reads==9,'expanded consume coverage')
 for i=0,3 do assert(ack[i]==math.floor(at/2^(8*i))%256,'consume token')end
'''+lua[b:]
 lua=once(lua,'clock()-setup','clock()-(setup or execute)')
 lua=once(lua,'at=at+1;reads=0;','at=at+1;descriptor_reads=0;reads=0;')
 lua=once(lua,'end,emu.callbackType.write,0x6010,0x601c)','end,emu.callbackType.write,0x604c,0x6059)')
 def guards():
  cases,names=base.guards()
  for name,start,count,op,seed in [('full3418',0,3418,4,b'\x39\xa2'),('raw240',3169,240,8,b'\x19\x27\x36\x45'),('raw9',3409,9,2,bytes(range(9)))]:
   h=bytearray(16);h[0]=op;h[1]=5
   for at,value in ((2,len(cases)+1),(4,1),(8,17),(10,start),(12,len(seed)),(14,0 if op==2 else count)):h[at:at+2]=value.to_bytes(2,'little')
   cases.append(bytes(h)+seed);names.append(name)
  return cases,names
 ns=dict(base.__dict__);ns.update(rom=rom,LUA=lua,guards=guards,__file__=__file__,__doc__=__doc__)
 source=once(inspect.getsource(base.main),'probes/nes-joint264/arm01/frame','probes/nes-joint274/arm01/frame')
 exec(compile(source,'consumer325-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
