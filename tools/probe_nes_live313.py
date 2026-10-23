# SPDX-License-Identifier: MIT
"""Development integration of the common host packet interpreter."""
import shutil
import probe_nes_live312 as old
from nes_executor313 import apply,observe
from nes_manifest313 import apply as manifest
from nes_consumer313 import apply as consumer,observe as consumer_observe
from nes_admission313 import apply as admission,observe as admission_observe
from nes_delta231 import ROOT,sha
previous_prepare=old.prepare

def prepare(*args,**kwargs):
    src,pins=previous_prepare(*args,**kwargs)
    d=args[0];apply(d);manifest(d);consumer(d);admission(d)
    p=d/'joint266_tb.sv';p.write_text(admission_observe(consumer_observe(observe(p.read_text()))),newline='\n')
    for n in ('nes_executor313.py','nes_manifest313.py','nes_consumer313.py','nes_admission313.py','probe_nes_live313.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins

old.old.old.prepare=prepare
old.old.old.__file__=__file__
if __name__=='__main__':old.old.old.main()
