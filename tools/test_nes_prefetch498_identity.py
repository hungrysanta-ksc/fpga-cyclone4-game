# SPDX-License-Identifier: MIT
"""498 actual runtime post-SEAL identity/EA test with modeled planner/display grant."""
import argparse,json
from pathlib import Path
from test_nes_prefetch498_arm import Probe
from check_nes_game478 import crc,sha
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
class Runtime(Probe):
 def __init__(self,arm,g,raw):
  self.ea=False;self.ops=[];super().__init__(arm,g,raw,'none')
  self.call('nes_resident211_reset',[self.resident]);self.put(self.s,'nes_native_sink165','state',0,1);self.put(self.s,'nes_native_sink165','serial',0,4)
 def hook(self,u,at,size,user):
  def ret(v):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  syms=getattr(self,'syms',{})
  if at==syms.get('nes_native_video211_plan'):
   self.put(self.video,'nes_native_video165','generation',907,2);ret(1);return
  if at==syms.get('nes_plan200_finish'):
   p=u.reg_read(UC_ARM_REG_R0)
   for k,v,n in [('finished',1,1),('started',1,1),('generation',907,2)]:self.put(p,'nes_plan200',k,v,n)
   ret(1);return
  if at==syms.get('nes_sink212_seal'):
   # Model old display ACK after the next input has reached COMPLETE.
   self.put(self.state,'nes_native165','state',2,1);self.put(self.state,'nes_native165','generation',908,2)
   for k,v,n in [('displayed',1,1),('last_generation',907,2),('state',0,1)]:self.put(self.s,'nes_native_sink165',k,v,n)
   ret(1);return
  if at==getattr(self,'spi',0):
   n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
   if tx[0]in[0xe8,0xea]:
    self.ops.append(tx.hex());rx=bytearray(n)
    if tx[0]==0xea:assert tx[1:3]==bytes([139,3]);self.ea=True
    else:rx[1:4]=bytes([215,4,1 if self.ea else 2]);rx[19]=crc(rx[1:19],8,7,0)
    u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx));ret(1);return
  super().hook(u,at,size,user)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['arm','baseline','data','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();g=(a.data/'frame908.geometry').read_bytes();raw=(a.data/'frame908.raw').read_bytes();rows=[]
 for src,candidate in [(a.baseline,False),(a.arm,True)]:
  m=Runtime(src,g,raw);ok=m.call('nes_runtime165_step',[m.rt]);row={'candidate':candidate,'ok':ok,'EA':m.ea,'display_generation':m.get(m.rt,'nes_native_runtime165','generation',2),'next_generation':m.get(m.state,'nes_native165','generation',2),'next_state':m.state_value(),'firmware_sha256':sha(src/'obj-nes-100/firmware.stm')}
  print(row, m.get(m.rt,'nes_native_runtime165','result'),flush=True)
  assert bool(ok)==candidate and m.ea==candidate and row['next_generation']==908 and row['next_state']==2
  if candidate:assert row['display_generation']==907
  rows.append(row)
 a.out.write_text(json.dumps({'passed':True,'scope':__doc__,'rows':rows},indent=2)+'\n');print(json.dumps(rows))
