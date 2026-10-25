# SPDX-License-Identifier: MIT
"""Actual aligned queue / immutable D4 reuse, unchanged ARM336 schedule."""
import shutil
import probe_nes_ingress337 as previous
from nes_ingress338 import apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    a=s.index('     if(i<16)begin\n      if(i>=4&&i<=9)begin')
    b=s.index('     ignore265=call263(1,i,b);',a)
    s=s[:a]+"     b=dut.flow.queue.buffer[(dut.flow.queue.retired[0]?768:512)+i];\n"+s[b:]
    p.write_text(s,newline='\n')
    for n in ('nes_ingress338.py','probe_nes_ingress338.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
