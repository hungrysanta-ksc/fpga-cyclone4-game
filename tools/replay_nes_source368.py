# SPDX-License-Identifier: MIT
"""Replay recorded SPI responses to recover causal ARM states, not new timing."""
import argparse,json,shutil,struct
from pathlib import Path
import probe_nes_hint367 as baseline
from nes_delta231 import once,sha

class Replay(baseline.Live367):
 def __init__(self,d,irq=False):
  super().__init__(d,False);self.seq=0
 def exchange(self,tx):
  self.seq+=1
  lines=(REFERENCE/f'arm-req{self.seq}').read_text().splitlines();count=int(lines[0].split()[0])
  expected=bytes.fromhex(lines[1]) if len(lines)>1 else b''
  got_count=self.phase367*512+len(tx) if self.phase367 else 261 if self.checkpoint_mode else 260 if tx is None else len(tx)
  assert (count,expected)==(got_count,tx or b''),('SPI replay mismatch',self.seq,count,got_count,expected[:16].hex(),(tx or b'')[:16].hex())
  lines=(REFERENCE/f'arm-rsp{self.seq}').read_text().splitlines();low,high,level=map(int,lines[0].split())
  rx=bytes.fromhex(lines[1]) if tx else b'';assert len(rx)==len(tx or b'')
  self.now=low+(high<<32);self.level=level;self.before=self.arm.instructions
  self.transfers.append(dict(tx=(tx or b'').hex(),rx=rx.hex(),RTL_ns=self.now,wait284=tx is None))
  if tx and tx[0]==0xe1:self.packets.append(tx[1:-2])
  self.arm.gpio(level);return rx

class Snap(baseline.ARM367):
 def hook(self,uc,address,size,user):
  if address==(self.symbols['source_hint367']&~1):
   state=bytes(uc.mem_read(self.symbols['receiver280'],28));serial=int.from_bytes(state[4:8],'little')
   self.snapshot368=getattr(self,'snapshot368',0)+1
   name=f'hint-state368-{serial}-{self.snapshot368}.bin'
   (self.endpoint.d/name).write_bytes(bytes(uc.mem_read(0x20000000,0x40000)))
   self.endpoint.snapshots.append(dict(serial=serial,name=name,state=state.hex(),geometry_groups=int.from_bytes(uc.mem_read(self.symbols['geometry_groups367'],4),'little')))
  super().hook(uc,address,size,user)

def main():
 global REFERENCE
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 REFERENCE=a.reference.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 for f in REFERENCE.iterdir():
  if f.is_file() and not f.name.startswith(('arm-req','arm-rsp')):shutil.copyfile(f,d/f.name)
 s=(REFERENCE/'executed-worker367.py').read_text();_,ns=baseline.worker_source()
 from nes_bg295 import unbatch as unbatch295
 from nes_bg293 import unbatch
 import os
 ns.update(ARM=Snap,Live=Replay,os=os,unbatch295=unbatch295,unbatch=unbatch)
 # Record only causal states. The original worker still independently checks
 # material, certificates and produced output against verification oracles.
 instances=[]
 original=Replay.__init__
 def init(self,*args,**kwargs):original(self,*args,**kwargs);self.snapshots=[];instances.append(self)
 Replay.__init__=init
 exec(compile(s,'source368-recorded-worker','exec'),ns);ns['worker'](d,909,False,True)
 result=dict(passed=True,new_timing=False,snapshots=instances[-1].snapshots,ELF=sha(d/'output.elf'),reference=str(REFERENCE),transactions=instances[-1].seq)
 (d/'replay368.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
