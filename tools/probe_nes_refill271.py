# SPDX-License-Identifier: MIT
"""Execute tile-ready backoff and E1 pre-admission status with actual ARM/SPI."""
import inspect,shutil
import probe_nes_refill267 as old
import probe_nes_refill270 as prior
from probe_nes_arm264 import ARM as BaseARM,UC_ARM_REG_R0
from nes_delta231 import ROOT,sha

class ARM(BaseARM):
 def __init__(self,*args,**kwargs):
  self.pause_calls=0;self.pause_iterations=0
  super().__init__(*args,**kwargs)
 def hook(self,uc,address,size,user):
  if address==(self.symbols.get('pause271',1)&~1):
   self.pause_calls+=1;self.pause_iterations+=uc.reg_read(UC_ARM_REG_R0)
  super().hook(uc,address,size,user)

class Live(old.Live):
 def transfer(self,tx):
  rx=super().transfer(tx)
  self.transfers[-1].update(pause_calls=self.arm.pause_calls,pause_iterations=self.arm.pause_iterations)
  return rx

def worker(*args,**kwargs):
 ns=dict(old.__dict__);ns.update(ARM=ARM,Live=Live)
 exec(compile(inspect.getsource(old.worker),'worker271','exec'),ns)
 return ns['worker'](*args,**kwargs)

def prepare(*args,**kwargs):
 d=args[0];src,pins=prior.prepare(*args,**kwargs)
 (d/'nes_spi270.sv').write_bytes((ROOT/'tools/nes_spi271.sv').read_bytes())
 src['nes_spi270.sv']=(d/'nes_spi270.sv').read_text()
 for n in ['nes_spi271.sv','nes_output271.c','probe_nes_refill271.py']:
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
 return src,pins

def build(d):
 prior.build(d)
 (d/'nes_output264.c').write_bytes((ROOT/'tools/nes_output271.c').read_bytes())

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,worker=worker,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill271-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
