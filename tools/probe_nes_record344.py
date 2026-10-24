# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_ingress338 as previous
from nes_record344 import apply,native
from nes_delta231 import ROOT,sha,once
engine=previous.engine
prepare0=engine.prepare

def prepare(*a,**k):
 src,pins=prepare0(*a,**k);d=a[0]
 if os.environ.get('NES344_ARM_ONLY')!='1':apply(d)
 p=d/'nes_bridge267.c';s=p.read_text();s=once(s,'while(!(f=fopen(path,"r"))) {','while(!(f=fopen(path,"r"))) { FILE *err=fopen("arm-error344","r");if(err){fclose(err);return fail267();}')
 p.write_text(s,newline='\n')
 for n in ('nes_record344.py','probe_nes_record344.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
init0=engine.ARM296.__init__
def init(self,*a,**k):
 init0(self,*a,**k)
 if 'advance344' in self.symbols:self.watch317[self.symbols['advance344']&~1]='advance344'
stamp0=engine.ARM296.stamp317
def stamp(self):
 r=stamp0(self)
 for n in ('prefixes344','run_first344','run_last344'):
  if n in self.symbols:r[n]=int.from_bytes(self.uc.mem_read(self.symbols[n],4),'little')
 return r
worker0=engine.worker
def worker(*a,**k):
 try:return worker0(*a,**k)
 except BaseException as e:
  (a[0]/'arm-error344').write_text(repr(e));raise
engine.prepare=prepare
if os.environ.get('NES344_RTL_ONLY')!='1':engine.native=native
engine.ARM296.__init__=init;engine.ARM296.stamp317=stamp;engine.worker=worker;engine.__file__=__file__
if __name__=='__main__':engine.main()
