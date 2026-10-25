# SPDX-License-Identifier: MIT
"""Actual M4/IRQ/ROM two-slot/expanded-response prerequisite experiment."""
import os,shutil
os.environ['NES307_RTL']='1'
import probe_nes_live307 as old
from nes_slots312 import native,apply,observe
from nes_record312 import apply as record
from nes_delta231 import ROOT,sha
old.old.native=native
previous_prepare=old.prepare
def prepare(*args,**kwargs):
    src,pins=previous_prepare(*args,**kwargs);d=args[0]
    apply(d)
    record(d)
    p=d/'joint266_tb.sv';p.write_text(observe(p.read_text()),newline='\n')
    for n in ('nes_slots312.py','nes_record312.py','probe_nes_live312.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
old.old.prepare=prepare
old.old.__file__=__file__
if __name__=='__main__':old.old.main()
