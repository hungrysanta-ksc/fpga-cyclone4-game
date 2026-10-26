# SPDX-License-Identifier: MIT
"""Actual M4 storage credit vs semantic completion, faults and held-SPI guards."""
import argparse,binascii,json
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from nes_delta231 import BASE,sha
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR

class Receive(ARM):
 def __init__(self,elf,blocks,mode):
  self.blocks=blocks;self.mode=mode;self.at=0;self.held=False;self.seen=False;self.acks=0;self.credits=[];self.hints=[];self.wakes=0;self.empty=False
  super().__init__(elf,None)
 def hook(self,uc,address,size,user):
  name=next((n for n in ('source_io367','physical267','irq_end284','irq_begin284','wait284') if address==(self.symbols[n]&~1)),None)
  if not name:return super().hook(uc,address,size,user)
  self.instructions+=1;p,n,phase=(uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
  if name=='source_io367':
   if phase==1:
    assert not self.held and not self.seen and n==13;self.held=True
    tx=bytes(uc.mem_read(p,n));assert tx[0]==0xd4 and tx[5]==0 and crc(tx[:6],8)==tx[6]
    self.empty=self.mode=='empty_wake' and not self.wakes
    block=b'' if self.empty else self.blocks[self.at];flags=0xa8|bool(block)|(0 if self.mode=='missing_last' else 2)
    h=bytearray([flags,len(block),self.at>>8,self.at&255]);h.append(crc(h,8))
    if self.mode=='header_crc':h[4]^=1
    if self.mode=='token':h[3]^=1;h[4]=crc(h[:4],8)
    if self.mode=='flags':h[0]^=4;h[4]=crc(h[:4],8)
    uc.mem_write(p,bytes(8)+h)
   else:
    assert self.held;self.held=False
    if n:
     b=self.blocks[self.at]
     if self.mode=='semantic' and not self.at:b=b'X'+b[1:]
     if self.mode=='generation' and not self.at:b=b[:16]+bytes([b[16]^3])+b[17:]
     if self.mode=='late_semantic' and self.at==len(self.blocks)-1:b=b[:-1]+bytes([b[-1]^1])
     c=crc(b)^(1 if self.mode=='payload_crc' or (self.mode=='payload_crc_second' and self.at==1) else 0);assert n==len(b)+2
     uc.mem_write(p,b+c.to_bytes(2,'big'));self.seen=True
     if self.mode=='cancel_before_credit':uc.mem_write(self.symbols['source_cancel367'],b'\1\0\0\0')
  elif name=='physical267':
   assert not self.held;tx=bytes(uc.mem_read(p,n))
   if tx[0]==0xea:
    assert n==28 and crc(tx[:26])==int.from_bytes(tx[26:],'little')
    self.hints.append(dict(packet=tx.hex(),semantic_blocks=int.from_bytes(uc.mem_read(self.symbols['source_blocks367'],4),'little'),geometry_groups=int.from_bytes(uc.mem_read(self.symbols['geometry_groups367'],4),'little')))
    if self.mode=='cancel_hint':uc.mem_write(self.symbols['source_cancel367'],b'\1\0\0\0')
    uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert tx[0]==0xd5 and n==8 and tx[5] in (1,3)
   assert self.seen and crc(tx[:6],8)==tx[6] and int.from_bytes(tx[1:3],'big')==self.at
   if tx[5]==1:
    self.credits.append(int.from_bytes(uc.mem_read(self.symbols['source_blocks367'],4),'little'))
    if self.mode=='cancel_after_credit':uc.mem_write(self.symbols['source_cancel367'],b'\1\0\0\0')
   else:
    assert self.at==len(self.blocks)-1;self.acks+=1
   self.at+=1;self.seen=False
  elif name=='wait284':assert not self.held;self.wakes+=1
  uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 f=BASE/'probes/nes-capture365/early03/blocks.txt';blocks=[bytes.fromhex(x.split()[3]) for x in f.read_text().splitlines() if x.startswith('905 ')];rows=[]
 for mode in ('normal','empty_wake','header_crc','token','flags','payload_crc','semantic','generation','missing_last','cancel_before_credit','cancel_after_credit'):
  arm=Receive(a.source/'output.elf',blocks,mode)
  for n in ('reset259','reset285','reset280','source_reset367'):arm.call(n,[])
  ok=arm.call('source_receive367',[]);good=mode in ('normal','empty_wake')
  assert bool(ok)==good and arm.acks==int(good) and not arm.held,(mode,ok,arm.acks)
  if good:assert arm.at==len(blocks) and arm.credits[0]==0
  if mode in ('payload_crc','cancel_before_credit','header_crc','token','flags'):assert not arm.credits
  if mode in ('semantic','generation','cancel_after_credit'):assert arm.credits==[0]
  rows.append(dict(mode=mode,ok=ok,credits=len(arm.credits),semantic_before_credits=arm.credits,final_ACK=arm.acks,held_CS=arm.held))
 result=dict(passed=True,rows=rows,pins={str(p):sha(p) for p in (a.source/'output.elf',f,Path(__file__).resolve())})
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(rows))))
if __name__=='__main__':main()
