# SPDX-License-Identifier: MIT
import shutil,inspect
import probe_nes_owner319 as old
from nes_units323 import apply,native
from nes_delta231 import ROOT,sha,once
import probe_nes_refill274 as trace274
def cpu_trace(d,trace,s,pins,last):
    ns=dict(trace274.old.__dict__)
    code=once(inspect.getsource(trace274.ORIGINAL_CPU_TRACE),"r['CPU']['commands']==522","r['CPU']['commands']==546")
    exec(compile(code,'cpu323-trace','exec'),ns)
    return ns['cpu_trace'](d,trace,s,pins,last)
trace274.cpu_trace=cpu_trace
import probe_nes_live307 as observer307
original_verify=observer307.original_verify
def verify_units(pp,out):
    normalized=[]
    for p in out:
        if p[0] in (2,4,5,7,8):
            q=bytearray(p);domain=p[1];first=int.from_bytes(p[10:12],'little');count=int.from_bytes(p[14:16],'little')
            limit={0:1024,1:128,3:32,4:544,5:1121,6:128,7:16}[domain]
            assert count>0 and first+count<=limit
            shift=5 if domain==1 else 4 if domain in (0,3,6,7) else 0
            base=1121 if domain==6 else 3169 if domain==7 else 0
            size=(count<<shift)-(7 if domain==7 and first+count==16 else 0)
            q[1]=5 if domain in (6,7) else domain;q[10:12]=(base+(first<<shift)).to_bytes(2,'little')
            if p[0]==2:assert size==len(p)-16
            q[14:16]=(0 if p[0]==2 else size).to_bytes(2,'little');p=bytes(q)
        normalized.append(p)
    return original_verify(pp,normalized)
observer307.original_verify=verify_units
old.engine.native=native
previous=old.engine.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0];apply(d)
    for n in ('nes_units323.py','probe_nes_units323.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
old.engine.prepare=prepare
old.engine.__file__=__file__
if __name__=='__main__':old.engine.main()
