# SPDX-License-Identifier: MIT
"""Actual ARM inline serialization, CRC and four-credit transport model."""
import inspect,json
from nes_delta231 import ROOT,sha
import probe_nes_split274 as prior
from nes_inline275 import source,unwrap
from probe_nes_arm264 import crc

class Endpoint(prior.Endpoint):
 def __init__(self):
  super().__init__();self.physical=[]
 def transfer(self,tx):
  if tx[0]!=0xe1:return super().transfer(tx)
  assert crc(tx[:-2])==int.from_bytes(tx[-2:],'big')
  physical=bytes(tx[1:-2]);logical,program=unwrap(physical)
  transformed=bytes([0xe1])+logical
  transformed+=crc(transformed).to_bytes(2,'big')
  super().transfer(transformed)
  self.transfers[-1]=(bytes(tx),bytes(len(tx)));self.physical.append(physical)
  return bytes(len(tx))

def build(d):
 ns=dict(prior.__dict__);ns.update(source=source)
 exec(compile(inspect.getsource(prior.build),'inline275-build','exec'),ns)
 ns['build'](d)

def verify(pp,out):
 prior.verify(pp,[unwrap(p)[0] for p in out])

def main():
 ns=dict(prior.__dict__);ns.update(build=build,Endpoint=Endpoint,unwrap=unwrap)
 code=inspect.getsource(prior.main)
 code=code.replace("out=ep.packets[start:];verify(pp,out);", "out=ep.packets[start:];verify(pp,out);physical=ep.physical[start:];")
 code=code.replace('for p in out:', 'for p,wire in zip(out,physical):')
 code=code.replace('assert slot<=256,', 'assert unwrap(wire)==(p,program)\n   assert slot==len(wire)\n   assert slot<=256,')
 code=code.replace("for p in out))", "for p in physical))")
 code=code.replace('program_transmitted=False','program_transmitted=True')
 exec(compile(code,'inline275-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
