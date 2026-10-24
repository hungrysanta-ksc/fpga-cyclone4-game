# SPDX-License-Identifier: MIT
import json,shutil
import probe_nes_ingress338 as old
from nes_frontier342 import native
from nes_delta231 import ROOT,sha,once
engine=old.engine
prepare0=engine.prepare

def prepare(*args,**kwargs):
 src,pins=prepare0(*args,**kwargs);d=args[0]
 p=d/'nes_bridge267.c';s=p.read_text();s=once(s,'while(!(f=fopen(path,"r"))) {','while(!(f=fopen(path,"r"))) { FILE *err=fopen("arm-error342","r");if(err){fclose(err);return fail267();}')
 p.write_text(s,newline='\n')
 for n in ('nes_frontier342.py','probe_nes_frontier342.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
init0=engine.ARM296.__init__
def init(self,*a,**k):
 init0(self,*a,**k)
 self.watch317[self.symbols['advance342']&~1]='advance342'
stamp0=engine.ARM296.stamp317
def stamp(self):
 r=stamp0(self)
 for n in ('frontier342','prefixes342','checks342'):
  r[n]=int.from_bytes(self.uc.mem_read(self.symbols[n],4),'little')
 return r
engine.ARM296.stamp317=stamp
worker0=engine.worker
def worker(*a,**k):
 try:return worker0(*a,**k)
 except BaseException as e:
  (a[0]/'arm-error342').write_text(repr(e));raise
engine.prepare=prepare;engine.native=native;engine.ARM296.__init__=init;engine.worker=worker;engine.__file__=__file__
if __name__=='__main__':engine.main()
