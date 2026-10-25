# SPDX-License-Identifier: MIT
"""Passive M4 metadata timing on the NES315 executable and RTL."""
import json
import probe_nes_live315
import probe_nes_live305 as engine
from unicorn.arm_const import UC_ARM_REG_LR,UC_ARM_REG_R0

Base=engine.ARM296
instances=[]
class ARM317(Base):
    def __init__(self,*args):
        self.events317=[];self.calls317=[]
        super().__init__(*args);instances.append(self)
        self.watch317={self.symbols[n]&~1:n for n in ('next_step286','prepare289','prepare_slice309','issue_metadata317','tiles290') if n in self.symbols}
    def stamp317(self):
        e=self.endpoint;u=self.uc
        word=lambda n:int.from_bytes(u.mem_read(self.symbols[n],4),'little')
        state=bytes(u.mem_read(self.symbols['state259'],20))
        sent=int.from_bytes(state[:2],'little');retired=int.from_bytes(state[2:4],'little')
        return dict(instruction=self.instructions,anchor_RTL_ns=e.now,pending_instructions=self.instructions-e.before,
            modeled_ns=e.now+(self.instructions-e.before+e.exception_cycles)*1000/84,
            generation=int.from_bytes(state[6:8],'little'),sent=sent,retired=retired,pending=(sent-retired)&65535,
            plan_at=word('plan_at267'),plan_bytes=word('plan_bytes267'),plan_flags=word('plan_flags282'),
            IRQ_level=e.level,IRQ_pending=self.pending)
    def hook(self,uc,address,size,user):
        if not self.in_handler:
            for c in list(reversed(self.calls317)):
                if c['return']==address:
                    self.calls317.remove(c);r=uc.reg_read(UC_ARM_REG_R0)
                    if c['name']!='next_step286' or r==2:
                        self.events317.append(dict(name=c['name'],start=c['start'],end=self.stamp317(),result=r,arg=c['arg']))
            if address in self.watch317 and not(self.pending and self.enabled()):
                self.calls317.append(dict(name=self.watch317[address],**{'return':uc.reg_read(UC_ARM_REG_LR)&~1},
                    arg=uc.reg_read(UC_ARM_REG_R0),start=self.stamp317()))
        super().hook(uc,address,size,user)

engine.ARM296=ARM317
previous=engine.worker
def worker(*args,**kwargs):
    result=previous(*args,**kwargs)
    (args[0]/'metadata317.json').write_text(json.dumps(instances[-1].events317,indent=2)+'\n',newline='\n')
    return result
engine.worker=worker
engine.__file__=__file__
if __name__=='__main__':engine.main()
