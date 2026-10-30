# SPDX-License-Identifier: MIT
"""498 linked wait callback receives next input without prepare/COMMIT.
Transfer/ticks/service are fixtures; not common-clock or full runtime proof.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_hardware494_termination import SealDeadline
from check_nes_game478 import Machine,encode,sha
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
class Probe(SealDeadline):
 def __init__(self,arm,geometry,raw,fault):
  self.input_calls=[];self.input_fault=fault;self.cancelled=False;super().__init__(arm,'normal')
  self.packets,_,_=encode(geometry,raw,908);self.spi_calls=0;self.index=0;self.prepared=False;self.start_token=0
  self.put(self.state,'nes_native165','state',4,1);self.put(self.state,'nes_native165','generation',907,2)
  self.low_stack=0x2001e000;self.measure_wait=False
 def wait(self,args):
  self.measure_wait=True
  try:return self.call('wait498',args)
  finally:self.measure_wait=False
 def hook(self,u,at,size,user):
  if getattr(self,'measure_wait',False):self.low_stack=min(self.low_stack,u.reg_read(UC_ARM_REG_SP))
  if at==getattr(self,'service_cb',0) and self.cancelled:
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if at==getattr(self,'spi',0):
   n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
   if tx[0]in[0xd0,0xd1,0xd2,0xd3]:
    assert tx[0]!=0xd3,'early COMMIT';self.input_calls.append(tx[0]);rx=u.reg_read(UC_ARM_REG_R2)
    if self.input_fault=='IO':u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
    Machine.hook(self,u,at,size,user)
    if tx[0]==0xd2:
     if self.input_fault=='service_after_D2':self.cancelled=True
     if self.input_fault=='deadline_after_D2':self.expired=True
    if self.input_fault=='CRC'and tx[0]==0xd1:
     b=bytearray(u.mem_read(rx,n));b[-1]^=1;u.mem_write(rx,bytes(b))
    return
  super().hook(u,at,size,user)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['arm','data','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False);g=(a.data/'frame908.geometry').read_bytes();raw=(a.data/'frame908.raw').read_bytes();rows=[]
 for fault in ['none','IO','CRC','deadline','service_after_D2','deadline_after_D2']:
  m=Probe(a.arm,g,raw,fault);guard=m.get(m.w,'nes_sink_window184','guard',4)
  for reason,progress in [(0,0),(1,0),(2,1)]:assert m.wait([m.rt,guard,reason,progress]) and not m.input_calls
  if fault=='deadline':m.expired=True
  ok=1
  for i in range(len(m.packets)+5):
   ok=m.wait([m.rt,guard,2,0])
   if not ok or m.state_value()==2:break
  assert (ok and m.state_value()==2) if fault=='none' else not ok
  assert m.get(m.video,'nes_native_video165','generation',2)==907 and not m.prepared
  if fault=='none':
   assert m.get(m.state,'nes_native165','generation',2)==908
   before=len(m.input_calls);assert m.wait([m.rt,guard,2,0])and len(m.input_calls)==before
   layout=m.layout['nes_native165'];counts=struct.unpack_from('<6H',g,5728);offset=0
   for name,count,width,capacity in zip(['maps','rows','objects','exceptions','raster','palette'],counts,[2,1,8,4,8,1],[1056,224,128,128,224,64]):
    assert bytes(m.u.mem_read(m.state+layout[name],count*width))==g[offset:offset+count*width],name
    offset+=capacity*width
   assert bytes(m.u.mem_read(m.state+layout['raw_pixels'],len(raw)))==raw
  else:
   before=len(m.input_calls);assert not m.wait([m.rt,guard,2,0]) and len(m.input_calls)==before
  rows.append({'fault':fault,'ok':ok,'receiver_state':m.state_value(),'input_calls':len(m.input_calls),'old_video_generation':907,'D3':m.input_calls.count(0xd3),'runtime_result':m.get(m.rt,'nes_native_runtime165','result'),'isolated_callback_observed_stack_B':0x2001e000-m.low_stack})
 r={'passed':True,'scope':__doc__,'rows':rows,'firmware_sha256':sha(a.arm/'obj-nes-100/firmware.stm')};(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
