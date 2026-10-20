# SPDX-License-Identifier: MIT
"""Actual ARM backoff guards: bounded waits, progress reset and sticky fault."""
from pathlib import Path
import argparse,inspect,json,struct
import guard_nes_arm270 as old
from probe_nes_refill271 import ARM as BaseARM
from probe_nes_arm264 import UC_ARM_REG_R0,crc,plans
from nes_delta231 import sha

class Endpoint(old.Endpoint):
 def transfer(self,tx):
  if tx[0]!=0xe1:return super().transfer(tx)
  # Snapshot only: do not grant a modeled retirement just for piggybacking.
  service=self.service;self.service=lambda:None
  try:r=bytearray(super().transfer(bytes([0xe0])+bytes(23))[:9])
  finally:self.service=service
  self.transfers.pop();r[1]=0xf9;r[8]=crc(r[1:8],8)
  super().transfer(tx)
  reply=bytes(r)+bytes(len(tx)-9);self.transfers[-1]=(bytes(tx),reply)
  return reply

_bad=inspect.getsource(old.old.BadStatus.transfer).replace('super().transfer(tx)','Endpoint.transfer(self,tx)')
exec(compile('class BadStatus(Endpoint):\n def __init__(self,case):super().__init__();self.case=case\n'+_bad,'arm271-badstatus','exec'))

class ARM(BaseARM):
 def __init__(self,*args,**kwargs):
  self.budgets=[]
  super().__init__(*args,**kwargs)
 def hook(self,uc,address,size,user):
  if address==(self.symbols.get('pause271',1)&~1):self.budgets.append(uc.reg_read(UC_ARM_REG_R0))
  super().hook(uc,address,size,user)

class Hold(Endpoint):
 def __init__(self,case):
  super().__init__();self.case=case;self.held=0
 def transfer(self,tx):
  r=bytearray(super().transfer(tx))
  if tx[0]==0xe2 and r[7]&2 and r[3:5]==r[5:7]:
   maximum=1<<30 if self.case=='timeout' else 16
   if self.held<maximum:
    self.held+=1;r[7]&=~2
    if self.case=='progress':r[7]=1 if self.held<=6 else 0
    if self.case=='fault' and self.held==6:r[2]|=128
    r[8]=crc(r[1:8],8)
  return bytes(r)

def main():
 old.Endpoint=Endpoint
 old.BadStatus=BadStatus
 old.main()
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior,groups=plans();pp=groups[1];blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp);checks=[]
 for case in ['release','progress','fault','timeout']:
  ep=Hold(case);ep.begin(1,pp);arm=ARM(a.arm/'output.elf',ep);arm.call('reset259',[])
  arm.uc.mem_write(0x20010000,blob);arm.uc.mem_write(0x20018000,(prior/'expected-1.bin').read_bytes())
  arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  ok=arm.call('frame259',[0x20010000,len(blob),1,1])
  error=arm.uc.mem_read(arm.symbols['state259']+17,1)[0]
  assert arm.budgets and all(128<=n<=2048 and n&(n-1)==0 for n in arm.budgets),case
  if case in ('release','progress'):
   assert ok==1 and error==0 and ep.held==16,case
   assert arm.budgets[:3]==[128,256,512]
   if case=='progress':assert arm.budgets.count(128)>=2
  else:
   assert ok==0 and error==(2 if case=='fault' else 17),(case,error)
   before=len(ep.transfers);packets=len(ep.packets)
   assert arm.call('frame259',[0x20010000,len(blob),1,1])==0
   assert len(ep.transfers)==before and len(ep.packets)==packets
   if case=='timeout':assert 1024<=ep.held<=1032 and len(arm.budgets)==1023 and max(arm.budgets)==2048
  checks.append(dict(case=case,passed=True,held=ep.held,pause_calls=len(arm.budgets),pause_iterations=sum(arm.budgets),
   max_pause_iterations=max(arm.budgets),first_budgets=arm.budgets[:12],error=error,instructions=arm.instructions))
 snapshot=[]
 class BadE1(Endpoint):
  def __init__(self,case):super().__init__();self.case=case
  def transfer(self,tx):
   r=bytearray(super().transfer(tx))
   if tx[0]==0xe1:
    if self.case==0:r[8]^=1;return bytes(r)
    if self.case==1:r[1]=0xf8
    if self.case==2:r[4]=1 # current admission must NOT be in the snapshot
    if self.case==3:r[6]=1
    if self.case==4:r[2]|=4
    if self.case==5:r[2]|=128
    r[8]=crc(r[1:8],8)
   return bytes(r)
 for case,error in enumerate([2,2,3,3,3,2]):
  ep=BadE1(case);ep.begin(1,pp);arm=ARM(a.arm/'output.elf',ep);arm.call('reset259',[])
  arm.uc.mem_write(0x20010000,blob);arm.uc.mem_write(0x20018000,(prior/'expected-1.bin').read_bytes())
  arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  assert arm.call('frame259',[0x20010000,len(blob),1,1])==0
  assert arm.uc.mem_read(arm.symbols['state259']+17,1)[0]==error
  assert len(ep.packets)==1 and int.from_bytes(arm.uc.mem_read(arm.symbols['state259'],2),'little')==0
  before=len(ep.transfers);assert arm.call('frame259',[0x20010000,len(blob),1,1])==0 and len(ep.transfers)==before
  snapshot.append(dict(case=case,error=error,current_packet_may_be_accepted=True,sticky_no_retry=True))
 r=json.loads((a.out/'result.json').read_text());r.update(backoff_guards=checks,script_sha256=sha(Path(__file__)))
 r['E1_snapshot_guards']=snapshot
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(checks))

if __name__=='__main__':main()
