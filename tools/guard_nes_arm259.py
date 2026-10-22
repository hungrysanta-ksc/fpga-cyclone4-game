# SPDX-License-Identifier: MIT
"""Fault injection into the same compiled ARM serializer; no full RUN claim."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm259 import ARM,Endpoint,plans,crc,u16,BASE,sha,verify

class BadStatus(Endpoint):
 def __init__(self,case):super().__init__();self.case=case
 def transfer(self,tx):
  r=bytearray(super().transfer(tx))
  if tx[0]!=0xe0:return bytes(r)
  if self.case==1:r[23]^=1;return bytes(r)
  if self.case==2:r[4]^=1
  if self.case==3:r[6]=(self.accepted+1)&255
  if self.case==4:r[21]^=1
  if self.case==5:r[16]^=1
  if self.case==6:r[7]&=~1
  if self.case==7:r[1]=0xf7
  if self.case==8 and self.closed:r[8:12]=b'\xff'*4
  r[23]=crc(r[1:23],8);return bytes(r)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 prior,groups=plans();packets=groups[1];base=b''.join(len(p).to_bytes(2,'little')+p for p in packets);meta=(prior/'expected-1.bin').read_bytes();results=[]
 expected=[2,3,3,17,17,9,2,10,12,15,19,11]
 for case in range(1,13):
  endpoint=BadStatus(case);endpoint.begin(1,packets);arm=ARM(a.arm/'output.elf',endpoint);arm.call('reset259',[]);blob=bytearray(base);material=bytearray(meta);serial=1
  if case==9:blob=blob[:-1]
  if case==10:
   at=0
   while blob[at+2]!=9:at+=u16(blob,at)+2
   blob[at+2+16]=0
  if case==11:material[5152+3170]=7
  if case==12:serial=0
  arm.uc.mem_write(0x20010000,bytes(blob));arm.uc.mem_write(0x20018000,bytes(material));arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  assert arm.call('frame259',[0x20010000,len(blob),serial,1])==0
  code=arm.uc.mem_read(arm.symbols['state259']+17,1)[0];assert code==expected[case-1],(case,code)
  before=len(endpoint.transfers);assert arm.call('frame259',[0x20010000,len(blob),serial,1])==0 and len(endpoint.transfers)==before
  assert not any(p[0]==3 for p in endpoint.packets)
  results.append(dict(case=case,error=code,sticky_no_more_SPI=True,no_SEAL=True))
 endpoint=Endpoint();endpoint.begin(1,packets);endpoint.accepted=endpoint.retired=65530
 arm=ARM(a.arm/'output.elf',endpoint);arm.call('reset259',[]);arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',65530,65530))
 arm.uc.mem_write(0x20010000,base);arm.uc.mem_write(0x20018000,meta);arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
 assert arm.call('frame259',[0x20010000,len(base),1,1])==1
 verify(packets,endpoint.packets);assert endpoint.accepted==endpoint.retired<65530 and endpoint.max_used==4
 result=dict(passed=True,counter_wrap=dict(start=65530,final=endpoint.accepted,packets=len(endpoint.packets),max_credit=endpoint.max_used),cases=results,ELF_sha256=sha(a.arm/'output.elf'),scope=__doc__,descriptions=['bad status CRC','accepted counter mismatch','retired beyond pending','tile generation mismatch','tile length mismatch','missing tile-end barrier','old F7 status','token exhaustion','truncated plan','invalid packed map tag','bad HDMA meaning','invalid serial'])
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
