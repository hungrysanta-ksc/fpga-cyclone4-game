# SPDX-License-Identifier: MIT
"""Actual early manifest credit/IRQ path; NES307_RTL selects joint RTL."""
import os,json,shutil
import probe_nes_live305 as old
from nes_ingress307 import native
from nes_delta231 import ROOT,sha
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1

BaseARM=old.ARM296
instances=[]
class ARM307(BaseARM):
    def __init__(self,*args):
        self.issue307=[];super().__init__(*args);instances.append(self)
    def hook(self,uc,address,size,user):
        if address==(self.symbols['physical267']&~1):
            n=uc.reg_read(UC_ARM_REG_R1)
            if 0<n<=1024:
                b=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),n))
                if b[0]==0xe1:
                    state=bytes(uc.mem_read(self.symbols['state259'],20))
                    sent=int.from_bytes(state[:2],'little');retired=int.from_bytes(state[2:4],'little')
                    assert ((sent-retired)&65535)<4,'E1 issued without credit'
                    self.issue307.append(dict(instruction=self.instructions,op=b[1],bytes=n,sent=sent,retired=retired,
                        pending=(sent-retired)&65535,generation=int.from_bytes(state[6:8],'little'),
                        prior_RTL_ns=self.endpoint.transfers[-1]['RTL_ns'] if self.endpoint.transfers else None))
        super().hook(uc,address,size,user)

old.native=native;old.ARM296=ARM307
original_prepare=old.prepare
def prepare(*args,**kwargs):
    src,pins=original_prepare(*args,**kwargs);d=args[0]
    if os.environ.get('NES307_RTL')=='1':
        from nes_ingress307 import apply,reference
        apply(d);reference(d)
    for n in ('nes_ingress307.py','probe_nes_live307.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins

original_worker=old.worker
original_verify=old.old.previous.verify
def verify(pp,out):
    from analyze_nes_ingress306 import decode
    normalized=[]
    for p in out:
        if p[0]==15 and p[1]==1:
            assert p[40]==1
            q=bytearray(p[:40]);q[1]=0;q[12:14]=(190).to_bytes(2,'little');q.extend(decode(p[41:],166));p=bytes(q)
        normalized.append(p)
    return original_verify(pp,normalized)
old.old.previous.verify=verify
def worker(*args,**kwargs):
    result=original_worker(*args,**kwargs)
    (args[0]/'issue307.json').write_text(json.dumps(instances[-1].issue307,indent=2)+'\n',newline='\n')
    return result

old.prepare=prepare;old.worker=worker;old.__file__=__file__
if __name__=='__main__':old.main()
