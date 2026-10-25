# SPDX-License-Identifier: MIT
import shutil
import probe_nes_raster355 as previous
from nes_host359 import apply
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];apply(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('dut.flow.tap_pos278','dut.flow.tap_address278')
 s=once(s,'if(dut.core.validator.v_range_valid&&v_ready)', 'if(dut.core.validator.unit_event359)')
 s=once(s,'dut.core.validator.v_map_range,dut.core.validator.v_first,$time', 'dut.core.validator.unit_map359,dut.core.validator.unit_first359,$time')
 p.write_text(s,newline='\n')
 for n in ('nes_host359.py','probe_nes_host359.py'):shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
