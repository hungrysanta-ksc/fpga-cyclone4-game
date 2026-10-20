# SPDX-License-Identifier: MIT
"""Retained identity/preflight/wrap guards plus short-status corruption."""
import argparse,inspect,json,struct
from pathlib import Path
import guard_nes_arm264 as old
from probe_nes_arm264 import ARM,BatchEndpoint,crc,plans

class Endpoint(BatchEndpoint):
 def transfer(self,tx):
  if tx[0]!=0xe2:return super().transfer(tx)
  assert len(tx)==9
  r=bytearray(super().transfer(bytes([0xe0])+bytes(23))[:9]);r[1]=0xf9;r[8]=crc(r[1:8],8)
  self.transfers[-1]=(bytes(tx),bytes(r));return bytes(r)

class BadStatus(Endpoint):
 def __init__(self,case):super().__init__();self.case=case
 transfer=old.BadStatus.transfer

# Rebind zero-argument super through an explicit call for the inherited guard.
_source=inspect.getsource(old.BadStatus.transfer).replace('super().transfer(tx)','Endpoint.transfer(self,tx)')
exec(compile('class BadStatus(Endpoint):\n def __init__(self,case):super().__init__();self.case=case\n'+_source,'arm270-badstatus','exec'))

def main():
 ns=dict(old.__dict__);ns.update(Endpoint=Endpoint,BadStatus=BadStatus,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'arm270-guards','exec'),ns);ns['main']()
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior,groups=plans();pp=groups[1];blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp);extra=[]
 class BadShort(Endpoint):
  def __init__(self,case):super().__init__();self.case=case
  def transfer(self,tx):
   r=bytearray(super().transfer(tx))
   if tx[0]==0xe2:
    if self.case==0:r[8]^=1;return bytes(r)
    if self.case==1:r[1]=0xf8
    if self.case==2:r[4]^=1
    if self.case==3:r[6]=1
    if self.case==4:r[2]|=4
    if self.case==5:r[2]|=128
    r[8]=crc(r[1:8],8)
   return bytes(r)
 for case,error in enumerate([2,2,3,3,3,2]):
  ep=BadShort(case);ep.begin(1,pp);arm=ARM(a.arm/'output.elf',ep);arm.call('reset259',[])
  arm.uc.mem_write(0x20010000,blob);arm.uc.mem_write(0x20018000,(prior/'expected-1.bin').read_bytes());arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
  assert arm.call('frame259',[0x20010000,len(blob),1,1])==0
  assert arm.uc.mem_read(arm.symbols['state259']+17,1)[0]==error and not ep.packets
  before=len(ep.transfers);assert arm.call('frame259',[0x20010000,len(blob),1,1])==0 and len(ep.transfers)==before
  extra.append(dict(case=case,error=error,no_packet=True,sticky_no_SPI=True))
 path=a.out/'result.json';r=json.loads(path.read_text());r['short_status_guards']=extra;path.write_text(json.dumps(r,indent=2)+'\n');print('short-status corruption guards:',len(extra))

if __name__=='__main__':main()
