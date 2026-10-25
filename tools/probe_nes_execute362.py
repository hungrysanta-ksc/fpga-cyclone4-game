# SPDX-License-Identifier: MIT
import shutil
import probe_nes_cancel358 as previous
from nes_host359 import apply as host
from nes_execute362 import apply
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];host(d);apply(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('dut.flow.tap_pos278','dut.flow.tap_address278')
 s=once(s,'if(dut.core.validator.v_range_valid&&v_ready)', 'if(dut.core.validator.unit_event359)')
 s=once(s,'dut.core.validator.v_map_range,dut.core.validator.v_first,$time', 'dut.core.validator.unit_map359,dut.core.validator.unit_first359,$time')
 s=once(s,' task clear_output;',r'''
 integer crc_source362=0,crc_check362=0;
 wire check_use362=(dut.core.validator.state==dut.core.validator.H_BYTES||dut.core.validator.state==dut.core.validator.H_SCROLL)?dut.core.validator.h_valid:
  dut.core.validator.state==dut.core.validator.H_HASHBYTE||(dut.core.validator.state==dut.core.validator.H_CERT&&dut.core.validator.h_count<30);
 wire source_use362=dut.core.transport_crc_pending||(dut.core.encoder.state==dut.core.encoder.SBYTE&&dut.core.encoder.byte_valid&&dut.core.encoder.byte_ready);
 always @(posedge host_clk)if(!reset&&!dut.core.fault)begin
  if(source_use362)begin crc_source362++;if(dut.core.output_phase)$fatal(1,"source CRC owner362");end
  if(check_use362)begin crc_check362++;if(!dut.core.output_phase)$fatal(1,"checker CRC owner362");end
  if(source_use362&&check_use362)$fatal(1,"CRC overlap362");
 end
 final $display("CRC362 source=%0d checker=%0d",crc_source362,crc_check362);
 task clear_output;''')
 p.write_text(s,newline='\n')
 for n in ('nes_host359.py','nes_execute362.py','probe_nes_execute362.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
