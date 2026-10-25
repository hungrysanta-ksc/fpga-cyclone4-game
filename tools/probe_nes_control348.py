# SPDX-License-Identifier: MIT
import shutil
import probe_nes_ingress338 as previous
from nes_control348 import apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old=engine.prepare
def prepare(*a,**k):
 src,pins=old(*a,**k);d=a[0];apply(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('dut.flow.state==dut.flow.EXPAND325','dut.flow.state==dut.flow.ISSUE346&&dut.flow.repeat325&&!dut.flow.prelude_mode&&!dut.flow.meta346');p.write_text(s,newline='\n')
 for n in ('nes_control348.py','nes_plan348.py','probe_nes_control348.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
