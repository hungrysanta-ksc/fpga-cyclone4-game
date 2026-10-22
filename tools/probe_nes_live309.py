# SPDX-License-Identifier: MIT
"""Passive actual-M4 readiness/cost observations and optional ARM-only prep."""
import json,shutil
import probe_nes_live307 as old
from nes_prepare309 import native
from nes_delta231 import ROOT,sha
from unicorn.arm_const import UC_ARM_REG_LR,UC_ARM_REG_R0

Base=old.ARM307
instances=[]
class ARM309(Base):
    def __init__(self,*args):
        self.events309=[];self.calls309=[];super().__init__(*args);instances.append(self)
        self.watch309={self.symbols[n]&~1:n for n in ('next_step286','prepare289','prepare_slice309') if n in self.symbols}
    def stamp309(self):
        e=self.endpoint
        return dict(instruction=self.instructions,anchor_RTL_ns=e.now,
                    pending_instructions=self.instructions-e.before,
                    modeled_ns=e.now+(self.instructions-e.before+e.exception_cycles)*1000/84)
    def hook(self,uc,address,size,user):
        if not self.in_handler:
            for c in list(reversed(self.calls309)):
                if c['return']==address:
                    self.calls309.remove(c);r=uc.reg_read(UC_ARM_REG_R0)
                    if c['name']!='next_step286' or r==2:
                        self.events309.append(dict(name=c['name'],generation=int.from_bytes(uc.mem_read(self.symbols['state259']+6,2),'little'),
                            start=c['start'],end=self.stamp309(),result=r,
                            prepared=int.from_bytes(uc.mem_read(self.symbols['prepared309'],4),'little') if 'prepared309' in self.symbols else None))
            if address in self.watch309 and not (self.pending and self.enabled()):
                self.calls309.append(dict(name=self.watch309[address],return_=0,**{'return':uc.reg_read(UC_ARM_REG_LR)&~1},start=self.stamp309()))
        super().hook(uc,address,size,user)

old.old.native=native
old.old.ARM296=ARM309
original_prepare=old.prepare
def prepare(*args,**kwargs):
    src,pins=original_prepare(*args,**kwargs);d=args[0]
    for n in ('nes_prepare309.py','probe_nes_live309.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
original_worker=old.worker
def worker(*args,**kwargs):
    result=original_worker(*args,**kwargs)
    (args[0]/'prepare309.json').write_text(json.dumps(instances[-1].events309,indent=2)+'\n',newline='\n')
    return result
old.old.prepare=prepare;old.old.worker=worker;old.old.__file__=__file__
if __name__=='__main__':old.old.main()
