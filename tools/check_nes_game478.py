# SPDX-License-Identifier: MIT
"""Current linked M4 on pinned SMB3 captures; host2232 encoder and SPI/plan stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def crc(data,width,poly,initial):
 c=initial
 for b in data:
  c^=b<<(width-8)
  for _ in range(8):c=((c<<1)^(poly if c&(1<<(width-1)) else 0))&((1<<width)-1)
 return c
def next_y(v):
 low=v&32767
 if low&0x7000!=0x7000:low+=0x1000
 else:
  low&=~0x7000;y=(low>>5)&31
  if y==29:low=(low&~0x3e0)^0x800
  elif y==31:low&=~0x3e0
  else:low+=32
 return (v&~32767)|low

def encode(geometry,raw,generation):
 assert len(geometry)==5741
 counts=struct.unpack_from('<6H',geometry,5728);patches=geometry[5740]
 assert len(raw)==patches*256
 arrays=[];offset=0
 for count,width,capacity in zip(counts,[2,1,8,4,8,1],[1056,224,128,128,224,64]):
  arrays.append([int.from_bytes(geometry[offset+i*width:offset+(i+1)*width],'little') for i in range(count)])
  offset+=capacity*width
 records=[]
 def add(kind,index,value):
  width=8 if kind==0 and index&0x1000 else [2,1,7,4,7,1,2,8][kind]
  records.append(struct.pack('>HH',(kind<<13)|index,generation)+value.to_bytes(width,'big'))
 header=(0x2232<<48)|((counts[0]//33)<<42)|((counts[5]//32)<<36)|(224<<28)|(counts[2]<<20)|(counts[3]<<12)|patches
 add(7,0,header)
 for kind,values in enumerate(arrays):
  at=0
  while at<len(values):
   left=len(values)-at;v=values[at]
   if kind in [1,5]:
    n=min(8,left);packed=int.from_bytes(bytes(values[at:at+n]),'big');add(7,0x1800|(kind<<8)|(n-1),packed)
   elif kind==0:
    n=1
    while n<min(256,left) and values[at+n]==v:n+=1
    if n>1:add(6,0x1000|(n-1),v)
    else:
     n=min(4,left);packed=0
     for cell in values[at:at+n]:packed=(packed<<15)|cell
     add(0,0x1000|at,(n<<60)|packed)
   else:
    n=1
    while n<min(256,left) and values[at+n]==v:n+=1
    if n>1:add(7,0x800|(kind<<8)|(n-1),v)
    elif kind==4 and not v&(1<<49):
     expected=next_y(v)
     while n<min(256,left) and values[at+n]==expected:
      n+=1;expected=next_y(expected)
     if n>1:add(7,0x1c00|(n-1),v)
     else:add(kind,at,v)
    else:add(kind,at,v)
   at+=n
 logical=sum(counts);add(7,4,logical<<16)
 for at in range(0,len(raw),10):
  colors=raw[at:at+10];packed=0
  for color in colors:assert color<64;packed=(packed<<6)|color
  add(7,0x1000|at,(len(colors)<<60)|packed)
 add(7,1,((logical+len(raw))<<16)|len(raw))
 packets=[];current=bytearray()
 for record in records:
  if len(current)+len(record)>256:packets.append(bytes(current));current.clear()
  current+=record
 if current:packets.append(bytes(current))
 packets.append(struct.pack('>HHQ',0xe003,generation,0))
 return packets,counts,arrays

class Machine:
 def __init__(self,src,palette):
  self.src=src;self.layout={};self.instructions=0;self.plans=[];self.token=0
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);self.u.mem_map(0x08000000,0x80000);self.u.mem_map(0x20000000,0x20000)
  flash=(src/'obj-nes-100/firmware.stm').read_bytes()
  with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
   e=ELFFile(f)
   for s in e.iter_segments():
    if s['p_type']!='PT_LOAD' or not s['p_filesz']:continue
    b=s.data();at=s['p_paddr']-0x0800c000;assert flash[at:at+len(b)]==b;self.u.mem_write(s['p_vaddr'],b)
   self.syms={s.name:s['st_value']&~1 for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC'}
   for cu in e.get_dwarf_info().iter_CUs():
    for d in cu.iter_DIEs():
     if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or not d.attributes.get('DW_AT_byte_size'):continue
     name=d.attributes['DW_AT_name'].value.decode()
     if name not in ['nes_native165','nes_native_video165','nes_resident211','nes_plan191']:continue
     item={'size':d.attributes['DW_AT_byte_size'].value}
     for c in d.iter_children():
      if c.tag!='DW_TAG_member':continue
      off=c.attributes['DW_AT_data_member_location'].value
      if not isinstance(off,int):
       assert off[0]==0x23;value=shift=0
       for byte in off[1:]:
        value|=(byte&127)<<shift
        if byte<128:break
        shift+=7
       off=value
      if c.attributes.get('DW_AT_name'):item[c.attributes['DW_AT_name'].value.decode()]=off
      else:
       union=c.get_DIE_from_attribute('DW_AT_type')
       assert union.tag=='DW_TAG_union_type'
       for member in union.iter_children():
        if member.attributes.get('DW_AT_name'):item[member.attributes['DW_AT_name'].value.decode()]=off
     if name in self.layout:assert self.layout[name]==item
     self.layout[name]=item
  self.state,self.video,self.resident,self.lut=0x20008000,0x2000b000,0x2000f000,0x20011000
  assert self.state+self.layout['nes_native165']['size']<=self.video
  assert self.video+self.layout['nes_native_video165']['size']<=self.resident
  assert self.resident+self.layout['nes_resident211']['size']<=self.lut
  self.end,self.spi,self.writer=0x0807fff0,0x0807ffe0,0x0807ffd0
  self.u.hook_add(UC_HOOK_CODE,self.hook);self.u.mem_write(self.lut,palette)
  self.call('nes_native165_reset',[self.state]);self.call('nes_resident211_reset',[self.resident])
 def state_value(self):return self.u.mem_read(self.state+self.layout['nes_native165']['state'],1)[0]
 def status(self):
  ready=self.index<len(self.packets) and (self.index<len(self.packets)-1 or self.prepared)
  b=bytearray(8);b[1]=0xd6;b[2]=int(ready)|(2 if self.state_value()>=2 else 0)
  b[3:5]=((self.start_token+self.index)&65535).to_bytes(2,'big')
  if ready:b[5:7]=len(self.packets[self.index]).to_bytes(2,'big')
  b[7]=crc(b[1:7],8,7,0);return bytes(b)
 def hook(self,u,at,size,user):
  if at==self.end:u.emu_stop();return
  if at==self.writer:
   self.plans.append([u.reg_read(UC_ARM_REG_R1),bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),self.layout['nes_plan191']['size'])).hex()])
  elif at==self.spi:
   n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));op=tx[0]
   if op==0xd0:rx=self.status()
   elif op==0xd1:
    b=self.packets[self.index];assert n==len(b)+3;rx=b'\0'+b+crc(b,16,0x1021,65535).to_bytes(2,'big')
   elif op==0xd2:
    assert int.from_bytes(tx[2:4],'big')==((self.start_token+self.index)&65535);rx=self.status();self.index+=1
   else:
    assert op==0xd3 and tx[4]==1;rx=self.status();self.prepared=True
   assert len(rx)==n;u.mem_write(u.reg_read(UC_ARM_REG_R2),rx);self.spi_calls+=1
  else:self.instructions+=1;return
  u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def call(self,name,args):
  stack=0x2001e000
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
  for i,v in enumerate(args[4:]):self.u.mem_write(stack+i*4,struct.pack('<I',v))
  self.u.reg_write(UC_ARM_REG_SP,stack);self.u.reg_write(UC_ARM_REG_LR,self.end|1);self.u.reg_write(UC_ARM_REG_XPSR,0x01000000)
  self.u.emu_start(self.syms[name]|1,self.end+2,count=30000000);assert self.u.reg_read(UC_ARM_REG_PC)==self.end,name
  return self.u.reg_read(UC_ARM_REG_R0)
 def frame(self,packets,geometry,raw,generation,serial):
  self.packets=packets;self.index=0;self.prepared=False;self.start_token=self.token;self.spi_calls=0;before=self.instructions
  while self.index<len(packets):
   if self.state_value()==2:ok=self.call('nes_native165_prepare',[self.state,1,self.spi|1,0])
   else:ok=self.call('nes_native165_poll',[self.state,self.spi|1,0])
   assert ok==1,('receiver',self.index,self.state_value(),bytes(self.u.mem_read(self.state+self.layout['nes_native165']['error'],1)).hex())
  receive=self.instructions-before;assert self.state_value()==4;self.token=(self.start_token+len(packets))&65535
  layout=self.layout['nes_native165'];counts=struct.unpack_from('<6H',geometry,5728);offset=0
  for name,count,width,capacity in zip(['maps','rows','objects','exceptions','raster','palette'],counts,[2,1,8,4,8,1],[1056,224,128,128,224,64]):
   assert bytes(self.u.mem_read(self.state+layout[name],count*width))==geometry[offset:offset+count*width],name
   offset+=capacity*width
  assert bytes(self.u.mem_read(self.state+layout['raw_pixels'],len(raw)))==raw
  count_tiles=int.from_bytes(self.u.mem_read(self.state+layout['ntiles'],2),'little')
  assert self.call('nes_resident211_begin',[self.resident,1,1,generation,self.writer|1,0])==1
  self.plans=[];before=self.instructions
  assert self.call('nes_native_video211_plan',[self.state,self.lut,self.video,self.resident])==1,'planner'
  planner=self.instructions-before
  resident=self.layout['nes_resident211'];bank=self.u.mem_read(self.resident+resident['target'],1)[0]
  assert self.call('nes_resident211_commit',[self.resident,serial,generation,bank,1])==1
  data=bytes(self.u.mem_read(self.state,layout['size']))+bytes(self.u.mem_read(self.video,self.layout['nes_native_video165']['size']))+bytes(self.u.mem_read(self.resident,resident['size']))
  result={'receive_instructions':receive,'planner_instructions':planner,'state_sha256':hashlib.sha256(data).hexdigest(),'plans':list(self.plans),'tiles':count_tiles,'bank':bank,'source_SPI_calls':self.spi_calls}
  self.call('nes_native165_consumed',[self.state]);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['base','arm','dataset','palette','out']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 sealed=json.loads((a.dataset/'result.json').read_text());assert sealed['passed']
 palette=a.palette.read_bytes();assert len(palette)==128
 old,new=Machine(a.base,palette),Machine(a.arm,palette);results=[];inputs={}
 for serial,frame in enumerate(range(905,976),1):
  files=[a.dataset/f'frame{frame}.{ext}' for ext in ['geometry','raw']]
  for f in files:assert sha(f)==sealed['evidence_files'][f.name];inputs[f.name]=sha(f)
  geometry,raw=[f.read_bytes() for f in files];gen=frame&65535
  packets,counts,arrays=encode(geometry,raw,gen)
  x=old.frame(packets,geometry,raw,gen,serial);y=new.frame(packets,geometry,raw,gen,serial)
  assert x['state_sha256']==y['state_sha256'] and x['plans']==y['plans'],frame
  (a.out/f'frame{frame}.json').write_text(json.dumps({'baseline':x,'candidate':y},indent=2)+'\n')
  results.append({'frame':frame,'counts':counts,'raw_bytes':len(raw),'packets':len(packets),'payload':sum(map(len,packets)),'baseline':{k:v for k,v in x.items() if k!='plans'},'candidate':{k:v for k,v in y.items() if k!='plans'},'plan_count':len(y['plans'])})
  print(json.dumps({'frame':frame,'tiles':y['tiles'],'payload':sum(map(len,packets)),'receive':y['receive_instructions'],'planner':y['planner_instructions']}),flush=True)
 r={'passed':True,'frames':results,'input_sha256':inputs,'palette_sha256':sha(a.palette),'baseline_firmware':sha(a.base/'obj-nes-100/firmware.stm'),'candidate_firmware':sha(a.arm/'obj-nes-100/firmware.stm'),'scope':__doc__,'limits':'Host encoder is not new source RTL proof; synthetic transport/plan/DMA completion, isolated unit RAM128KiB; no IRQ/ROM waits/actual65816/fullRUN/game hardware/FPS or physical stack proof'}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
