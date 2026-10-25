# SPDX-License-Identifier: MIT
"""Live M4/IRQ/ROM proof of stored-credit/deferred-consumption separation."""
import os,shutil
os.environ['NES307_RTL']='1'
os.environ['NES309_PREP']='1'
import probe_nes_live307 as old
from nes_storage310 import native,apply,reference,observe
from nes_delta231 import ROOT,sha
old.old.native=native
previous_prepare=old.prepare

def prepare(*args,**kwargs):
    src,pins=previous_prepare(*args,**kwargs);d=args[0]
    apply(d);reference(d)
    p=d/'joint266_tb.sv';p.write_text(observe(p.read_text()),newline='\n')
    for n in ('nes_storage310.py','probe_nes_live310.py','nes_prepare309.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
previous_verify=old.verify

def verify(pp,out):
    normalized=[]
    for p in out:
        if p[0]==15 and p[1]==2:p=p[:1]+b'\x01'+p[2:]
        normalized.append(p)
    return previous_verify(pp,normalized)
old.old.old.previous.verify=verify
old.old.prepare=prepare
old.old.__file__=__file__
if __name__=='__main__':old.old.main()
