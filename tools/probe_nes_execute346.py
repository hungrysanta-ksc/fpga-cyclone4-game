# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_live340 as previous
import probe_nes_joint340 as joint
from nes_execute346 import source,host,native
from nes_delta231 import ROOT,sha
joint.apply=source
joint.host=host if os.environ.get('NES346_SOURCE_ONLY')!='1' else lambda d:None
engine=previous.engine
old=engine.prepare
def prepare(*a,**k):
 src,pins=old(*a,**k);d=a[0]
 if os.environ.get('NES346_SOURCE_ONLY')!='1':
  p=d/'joint266_tb.sv';s=p.read_text()
  s=s.replace('dut.flow.state==dut.flow.EXPAND325','dut.flow.state==dut.flow.ISSUE346&&dut.flow.repeat325&&!dut.flow.prelude_mode&&!dut.flow.meta346')
  p.write_text(s,newline='\n')
 for n in ('nes_execute346.py','probe_nes_execute346.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
