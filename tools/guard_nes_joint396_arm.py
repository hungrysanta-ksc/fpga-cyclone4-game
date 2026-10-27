# SPDX-License-Identifier: MIT
"""Execute compiled M4 prefill at the unaccounted-publication frontier.
The short dummy batch is a supply-loop fixture, not a hardware plan payload.
"""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from nes_delta231 import sha

class Endpoint:
 def __init__(self):self.arm=None;self.transfers=[];self.expected=0;self.accepted=0
 def transfer(self,tx):
  self.transfers.append(tx.hex())
  if tx[0]==0xe9:
   assert self.arm.uc.mem_read(self.arm.symbols['published396'],4)==struct.pack('<I',self.expected),'reservation must precede physical E9'
   self.accepted+=1
  else:assert tx[0]==0xe2,'no WFI/recursive SPI or other work before accounting'
  r=bytearray(len(tx));r[1]=0xfb;r[7]=1;r[8]=1;r[9:11]=self.accepted.to_bytes(2,'big')
  if len(r)>=14:r[13]=crc(r[1:13],8)
  return bytes(r)

def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 ep=Endpoint();arm=ARM(a.elf,ep);ep.arm=arm;arm.symbols['io259']=arm.symbols['physical267'];rows=[]
 def word(name,value):arm.uc.mem_write(arm.symbols[name],struct.pack('<I',value))
 for accounted in(0,50,10000):
  for delta in range(-5 if accounted else 0,36):
   for count in range(1,16):
    arm.call('seed287',[7])
    published=accounted+delta;allow=published+count<=accounted+33
    for n,v in dict(published396=published,accounted396=accounted,plan_cache282=1,plan_flags282=1,plan_accepted282=0,output_size285=6).items():word(n,v)
    arm.uc.mem_write(arm.symbols['output285'],bytes((3,0,count,0x83,7,0)))
    ep.transfers=[];ep.accepted=0;ep.expected=published+(count if allow else 0);before=arm.instructions
    ok=arm.call('prefill287',[])
    assert ok==1,(accounted,delta,count,ep.transfers,arm.uc.mem_read(arm.symbols['state259'],20).hex())
    final=struct.unpack('<I',arm.uc.mem_read(arm.symbols['published396'],4))[0]
    assert final==ep.expected and ep.accepted==int(allow) and ep.transfers[-1][:2]=='e2'
    assert struct.unpack('<I',arm.uc.mem_read(arm.symbols['accounted396'],4))[0]==accounted
    rows.append(dict(accounted=accounted,published=published,batch=count,admitted=allow,after=final,instructions=arm.instructions-before,commands=[x[:2]for x in ep.transfers]))
 (d/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
 result=dict(passed=True,cases=len(rows),ELF=sha(a.elf),case_sha=sha(d/'cases.json'),full_cases=sum(not r['admitted']for r in rows),accounted_ahead_cases=sum(r['published']<r['accounted']for r in rows),reservation_before_physical_E9=True,full_returns_to_accounting=True,scope=__doc__)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
