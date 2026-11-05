# SPDX-License-Identifier: MIT
"""Execute linked591 ARM D0-D4 against a one-sealed-packet endpoint model.

Real ARM binary; endpoint is Python, NOT FPGA/IRQ/ROM/65816 timing proof.
"""
import argparse,json,struct,zipfile
from pathlib import Path
from check_nes_game478 import Machine,encode,sha,crc as wirecrc
from analyze_nes_roles590 import summary,phase_packets,old_nonmap
from nes_transfer512 import legacy_packets
from nes_abi582 import canonical,crc
from analyze_nes_transport584 import elf_cost
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP

ROOT=Path(__file__).resolve().parents[1]

class Probe(Machine):
 def __init__(self,src):
  self.calls=[];self.low_sp=0x2001e000;self.have_frame=False
  super().__init__(src,bytes(128))
  self.set('r_epoch',1,4);self.toggle=0;self.token=65520;self.serial=0;self.previous=None
 def get(self,n,size=1):return int.from_bytes(self.u.mem_read(self.state+self.layout['nes_native165'][n],size),'little')
 def set(self,n,v,size=1):self.u.mem_write(self.state+self.layout['nes_native165'][n],v.to_bytes(size,'little'))
 def setup(self,geom,raw,g,fault='none',cold=False):
  self.arrays=encode(geom,raw,g)[2]+[list(raw)];self.g=g;self.serial+=1
  self.geom,self.raw=geom,raw;self.fault=fault;self.injected=False
  self.packets=[];self.index=0;self.prepared=False;self.read_seen=False;self.owned=True
  self.hello=False;self.wait='hello';self.repairs=0;self.accepted=False;self.frame_calls=[]
  self.start_token=self.token;self.have_frame=True
  self.meta,self.rawrec,_=old_nonmap(legacy_packets(geom,raw,g)[0]);self.cold=cold or self.previous is None
 def ready(self):
  return self.index<len(self.packets) and (self.packets[self.index][0]!=4 or self.prepared)
 def status(self):
  b=bytearray(8);b[1]=0xd6;b[2]=int(self.ready())|(2 if self.wait=='prepare' else 0)|(4*self.toggle)
  b[3:5]=self.token.to_bytes(2,'big')
  if self.ready():b[5:7]=len(self.packets[self.index]).to_bytes(2,'big')
  b[7]=wirecrc(b[1:7],8,7,0);return bytes(b)
 def summaries(self):
  a=self.arrays;n=len(a[0])//33
  begin=struct.pack('<HBBIIIH6HBB',0x591,1,int(not self.cold),1,self.serial,0 if self.cold else self.serial-1,self.g,*map(len,a[:6]),len(a[6])//256,0)
  records=[begin]
  if not self.cold:
   for i in range(n):
    row=a[0][i*33:(i+1)*33]
    # False but well-formed summary proves fresh CRC16 enforces repair.
    if self.fault=='false_summary' and i==0:row=self.previous[:33]
    records.append(summary(row))
  records.append(struct.pack('<HHHH',0x5900,n,crc(canonical([a[0]])),self.g))
  self.packets+=phase_packets(0,records)
  self.wait='cold_rows' if self.cold else 'request'
  if self.cold:self.replies((1<<n)-1)
 def replies(self,bitmap):
  n=len(self.arrays[0])//33;assert bitmap>>n==0
  rec=[]
  for i in range(n):
   if bitmap>>i&1:
    values=list(self.arrays[0][i*33:(i+1)*33])
    if self.fault in ('repair_once','repair_twice') and (not self.injected or self.fault=='repair_twice') and not rec:
     values[5]^=1;self.injected=True
    b=struct.pack('<BBHH',0,0,i*33,33)+struct.pack('<33H',*values)
    if self.fault=='bad_value' and not self.injected:b=b[:6]+b'\0\x80'+b[8:];self.injected=True
    if self.fault=='bad_index' and not self.injected:b=b[:2]+b'\x01\0'+b[4:];self.injected=True
    rec.append(b)
  if self.fault=='duplicate_row' and rec:rec.insert(0,rec[0])
  if self.fault=='missing_row' and rec:rec.pop()
  rec.append(struct.pack('<HHHH',0x5901,bitmap.bit_count(),crc(canonical([self.arrays[0]])),self.g))
  self.packets+=phase_packets(1,rec);self.wait='map_decision'
 def tail(self):
  a=self.arrays;metadata=canonical(a[:6]);full=canonical(a)
  meta=struct.pack('<HHHH',0xf004,len(metadata),sum(map(len,a[:6])),crc(metadata))
  end=struct.pack('<HHHH',0xf001,len(full),sum(map(len,a)),crc(full))
  if self.fault=='meta_crc':meta=meta[:-1]+bytes([meta[-1]^1])
  if self.fault=='end_crc':end=end[:-1]+bytes([end[-1]^1])
  self.packets+=phase_packets(2,self.meta+[meta])+phase_packets(3,self.rawrec+[end])
  self.packets+=phase_packets(4,[struct.pack('<HHI',0xf003,self.g,self.serial)])
  self.wait='prepare'
 def exchange(self,tx):
  op=tx[0];self.frame_calls.append((op,len(tx)));self.calls.append((op,len(tx)))
  if op==0xd0:return self.status()
  if op==0xd1:
   assert self.ready() and not self.read_seen
   b=self.packets[self.index];assert len(tx)==len(b)+3;self.read_seen=True
   c=crc(b)
   if self.fault=='wire_crc':c^=1
   return b'\0'+b+c.to_bytes(2,'big')
  if op==0xd2:
   assert self.read_seen and int.from_bytes(tx[2:4],'big')==self.token
   r=self.status();self.index+=1;self.token=(self.token+1)&65535;self.read_seen=False
   if self.fault=='D2_confirm':self.token=(self.token+1)&65535
   if self.index==len(self.packets) and self.wait=='prepare':self.owned=False
   return r
  if op==0xd3:
   assert self.wait=='prepare' and self.state_value()==2 and int.from_bytes(tx[2:4],'big')==self.g
   assert tx[4]==1;self.prepared=True;return self.status()
  assert op==0xd4 and len(tx)==24 and self.owned
  assert crc(tx[:20])==int.from_bytes(tx[20:22],'little') and tx[22:]==b'\x5a\xa5' and tx[1]==1 and tx[19]==0
  epoch,serial,gen,tok,bitmap=struct.unpack_from('<IIHHI',tx,2);mode=tx[18]
  assert epoch==1 and serial==self.serial
  if mode<2:
   assert self.wait=='hello' and not self.hello and gen==tok==bitmap==0 and mode==int(not self.cold)
   self.hello=True;self.summaries()
  else:
   assert self.index==len(self.packets) and gen==self.g and tok==(self.token-1)&65535
   if mode==2:
    assert self.wait=='request'
    if self.fault in ('none','right_shift'):
     expected=0
     for i in range(len(self.arrays[0])//33):
      old=self.previous[i*33:(i+1)*33];new=self.arrays[0][i*33:(i+1)*33]
      if not (new==old or new[:-1]==old[1:] or new[1:]==old[:-1]):expected|=1<<i
     assert bitmap==expected,('exact-value request oracle',bitmap,expected)
     if self.fault=='right_shift':assert not bitmap&1
    self.replies(bitmap)
   elif mode==3:
    assert self.wait=='map_decision' and self.repairs==0 and bitmap==(1<<(len(self.arrays[0])//33))-1
    self.repairs+=1;self.replies(bitmap)
   else:
    assert mode==4 and self.wait=='map_decision' and bitmap==0
    self.accepted=True;self.tail()
  if self.fault!='request_ack':self.toggle^=1
  return bytes(24)
 def hook(self,u,at,size,user):
  if at==self.spi:
   n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
   rx=self.exchange(tx);assert len(rx)==n;u.mem_write(u.reg_read(UC_ARM_REG_R2),rx)
   u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  self.low_sp=min(self.low_sp,u.reg_read(UC_ARM_REG_SP))
  super().hook(u,at,size,user)
 def run_frame(self):
  before=self.instructions
  for _ in range(250):
   if self.state_value()==4:break
   if self.state_value()==2:ok=self.call('nes_native165_prepare',[self.state,1,self.spi|1,0])
   else:ok=self.call('nes_native165_poll',[self.state,self.spi|1,0])
   if not ok:return dict(ok=False,error=self.get('error'),state=self.state_value(),repairs=self.repairs)
  else:raise AssertionError('loop watchdog')
  assert self.accepted and not self.owned and self.get('r_base') and self.get('r_serial',4)==self.serial
  offset=0
  for field,n,w,cap in zip(('maps','rows','objects','exceptions','raster','palette'),map(len,self.arrays[:6]),(2,1,8,4,8,1),(1056,224,128,128,224,64)):
   assert bytes(self.u.mem_read(self.state+self.layout['nes_native165'][field],n*w))==self.geom[offset:offset+n*w],field
   offset+=cap*w
  assert bytes(self.u.mem_read(self.state+self.layout['nes_native165']['raw_pixels'],len(self.raw)))==self.raw
  # Consumer call is a fixture for already completed final ACK+EA; NOT CPU proof.
  self.call('nes_native165_consumed',[self.state]);self.previous=list(self.arrays[0])
  return dict(ok=True,generation=self.g,instructions=self.instructions-before,packets=len(self.packets),
   payload_B=sum(map(len,self.packets)),wire_B=sum(n for _,n in self.frame_calls),calls=len(self.frame_calls),
   D4=sum(op==0xd4 for op,_ in self.frame_calls),repairs=self.repairs)

def baseline_frames(src,archive):
 m=Machine(src,bytes(128));token=65520;rows=[]
 with zipfile.ZipFile(archive) as z:
  for g in range(905,958):
   geom,raw=[z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw')]
   ps,_,_=legacy_packets(geom,raw,g)
   m.packets=ps;m.index=0;m.prepared=False;m.start_token=token;m.spi_calls=0;before=m.instructions
   while m.index<len(ps):
    ok=m.call('nes_native165_prepare',[m.state,1,m.spi|1,0]) if m.state_value()==2 else m.call('nes_native165_poll',[m.state,m.spi|1,0])
    assert ok,(g,m.index,m.state_value())
   assert m.state_value()==4;token=(token+len(ps))&65535
   m.call('nes_native165_consumed',[m.state])
   rows.append(dict(generation=g,instructions=m.instructions-before,packets=len(ps),payload_B=sum(map(len,ps)),calls=m.spi_calls))
 return rows

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('arm','base','archive','out'):ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 pins=json.loads((ROOT/'analysis/body581-verification.json').read_text());frames=[]
 m=Probe(a.arm)
 with zipfile.ZipFile(a.archive) as z:
  for g in range(905,958):
   geom,raw=[z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw')]
   import hashlib
   for ext,b in [('geometry',geom),('raw',raw)]:assert hashlib.sha256(b).hexdigest()==pins['inputs'][f'frame{g}.{ext}']
   m.setup(geom,raw,g);r=m.run_frame();assert r['ok'],(g,r);frames.append(r)
  geom,raw=[z.read('data/frame905.'+ext) for ext in ('geometry','raw')]
  guards=[]
  for fault in ('repair_once','repair_twice','wire_crc','request_ack','D2_confirm','bad_value','bad_index','duplicate_row','missing_row','meta_crc','end_crc'):
   p=Probe(a.arm);p.setup(geom,raw,905,fault);r=p.run_frame()
   assert r['ok']==(fault=='repair_once'),(fault,r)
   if not r['ok']:assert not p.get('r_base')
   guards.append(dict(fault=fault,**r))
  # Clock-domain STOP is not modeled. Reset during real ARM tentative receive
  # must invalidate base and make the next frame cold.
  for cut in (0,1,2,4):
   p=Probe(a.arm);p.setup(geom,raw,905)
   for _ in range(cut):assert p.call('nes_native165_poll',[p.state,p.spi|1,0])
   p.call('nes_native165_reset',[p.state]);p.set('r_epoch',1,4)
   assert not p.get('r_base');p.toggle=0;p.token=0;p.serial=0;p.previous=None
   p.setup(geom,raw,905,cold=True);r=p.run_frame();assert r['ok'];guards.append(dict(fault='reset_cut_'+str(cut),**r))
  for fault in ('false_summary','retained_RAM_corruption','right_shift'):
   p=Probe(a.arm);p.setup(geom,raw,905);assert p.run_frame()['ok']
   changed=bytearray(geom)
   if fault=='false_summary':changed[0]^=1
   elif fault=='retained_RAM_corruption':
    at=p.state+p.layout['nes_native165']['maps'];value=bytes(p.u.mem_read(at,1))[0]^1;p.u.mem_write(at,bytes([value]))
   else:changed[:66]=struct.pack('<33H',99,*struct.unpack('<33H',geom[:66])[:-1])
   p.setup(bytes(changed),raw,906,fault);r=p.run_frame();assert r['ok']
   assert r['repairs']==int(fault=='false_summary')
   guards.append(dict(fault=fault,**r))
 cost={label:dict(firmware_B=(src/'obj-nes-100/firmware.stm').stat().st_size,ELF_sha256=sha(src/'obj-nes-100/sd2snes.elf'),**elf_cost(src/'obj-nes-100/sd2snes.elf')) for label,src in [('577',a.base),('591',a.arm)]}
 reference=baseline_frames(a.base,a.archive)
 report=dict(stage=591,passed=True,frames=frames,baseline_frames=reference,guards=guards,linked_cost=cost,
  capacity_B=212992,excess_B=cost['591']['firmware_B']-212992,receiver_size_B=m.layout['nes_native165']['size'],
  observed_test_stack_B=0x2001e000-m.low_sp,scope=__doc__,new_FPGA=False,new_Questa=False,new_MAP=False,
  new_full_timeline=False,final_ACK_EA='unchanged runtime; consumed call is a fixture in this receiver test',
  pins=dict(checker_sha256=sha(Path(__file__)),source_sha256=sha(a.arm/'nes_native165.c'),header_sha256=sha(a.arm/'nes_native165.h'),archive_sha256=sha(a.archive)))
 (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('passed','linked_cost','excess_B','receiver_size_B','observed_test_stack_B')}))

if __name__=='__main__':main()
