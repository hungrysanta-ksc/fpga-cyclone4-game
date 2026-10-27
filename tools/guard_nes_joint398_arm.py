# SPDX-License-Identifier: MIT
"""Execute the real M4 producer ownership transitions under event credit.
The map bytes here are a serializer fixture, not a whole frame/pixel proof.
"""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM
from probe_nes_jobs394_arm import Endpoint
from nes_delta231 import sha

class CheckedEndpoint(Endpoint):
 def __init__(self):super().__init__(1);self.arm=None;self.END_phase=[]
 def transfer(self,tx):
  if tx[:2]==bytes([0xe1,0xa3]):self.END_phase.append(int.from_bytes(self.arm.uc.mem_read(self.arm.symbols['seal'],4),'little'))
  return super().transfer(tx)

def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);rows=[]
 def setup():
  ep=CheckedEndpoint();arm=ARM(a.elf,ep);ep.arm=arm;arm.symbols['io259']=arm.symbols['physical267'];arm.call('reset259',[])
  arm.uc.mem_map(0x40020000,0x1000);arm.uc.mem_write(0x40020410,(256).to_bytes(4,'little'))
  arm.uc.mem_write(arm.symbols['state259'],struct.pack('<4H2I2B',0,0,0,1,1,0,0,0))
  for n,v in dict(begin=1,seal=0,requirements264=1,map_at327=0,map_run327=0,map_tag327=0,map_size327=0,map_zero327=0,map_issued327=0,map_disabled327=0).items():arm.uc.mem_write(arm.symbols[n],struct.pack('<I',v))
  return arm,ep
 def command(arm,op=10):
  q=bytearray(17 if op==10 else 206);q[0]=op;q[1]=2 if op==10 else 0;q[4:8]=struct.pack('<I',1);q[8:10]=struct.pack('<H',1);q[12:14]=struct.pack('<H',len(q)-16)
  arm.uc.mem_write(0x2003d000,bytes(q));assert arm.call('dispatch289',[0x2003d000,len(q)])==1
 arm,ep=setup();command(arm)
 for _ in range(20):assert arm.call('issue_map327',[])==1
 rows.append(dict(case='legacy_owner_blocks_incremental',wire=[w.hex()for w in map(bytes.fromhex,ep.wire)],packet_count=len(ep.packets)))
 (d/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert len(ep.packets)==1 and ep.packets[0][0]==0xaa,'incremental duplicate emitted after legacy MAP'
 arm,ep=setup()
 for _ in range(20):assert arm.call('issue_map327',[])==1
 command(arm);assert len(ep.packets)==1 and ep.packets[0][0]==0xab
 rows.append(dict(case='incremental_owner_blocks_legacy',packet_count=len(ep.packets)))
 arm,ep=setup();command(arm,3);assert ep.END_phase==[1],'END was published before reserving terminal phase'
 rows.append(dict(case='END_reserved_before_physical_E1',phase_at_publication=ep.END_phase))
 (d/'cases.json').write_text(json.dumps(rows,indent=2)+'\n');report=dict(passed=True,ELF=sha(a.elf),cases=rows,pins={'cases.json':sha(d/'cases.json')},scope=__doc__)
 (d/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
