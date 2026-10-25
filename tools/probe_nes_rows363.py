# SPDX-License-Identifier: MIT
import shutil,sys
sys.argv.append('--keep-source')
import probe_nes_objpath362 as previous
from nes_rows363 import apply
from nes_delta231 import ROOT,sha,once
engine=previous.engine;old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];apply(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('dut.core.transport.publish','dut.core.transport.busy')
 s=s.replace('always @(posedge clk)begin\n  if(reset)published337','always @(posedge host_clk)begin\n  if(reset)published337').replace('always @(posedge clk)if(!reset&&dut.core.transport_crc_pending)','always @(posedge host_clk)if(!reset&&dut.core.transport_crc_pending)')
 s=s.replace('dut.core.encoder.state==dut.core.encoder.SREAD','dut.core.encoder.state==dut.core.encoder.SBYTE')
 s=s.replace('dut.flow.state==dut.flow.PCAP', '(dut.flow.state==dut.flow.PREAD&&dut.host_take363)')
 s=s.replace('call263(1,16+dut.flow.at,dut.flow.qdata)', 'call263(1,16+dut.flow.at,dut.flow.held)')
 s=s.replace('if(dut.core.ram_b_we&&dut.core.validator.state', 'if(dut.core.check_we363&&dut.core.validator.state')
 start=s.index(' always @(posedge clk)if(!reset)begin\n  if(dut.core.encoder.a_we');end=s.index(' reg [7:0] tx',start)
 block=s[start:end].replace('posedge clk','posedge host_clk').replace('  if(query)queries++;\n','')
 s=s[:start]+block+' always @(posedge clk)if(!reset&&query)queries++;\n'+s[end:]
 s=once(s,' task clear_output;',r'''
 integer rows363=0,bytes363=0,common363=0;
 always @(posedge host_clk)if(!reset&&!dut.core.fault)begin
  if(dut.core.row_take363)rows363++;
  if(dut.source_take363)bytes363++;
  if(dut.host_take363)common363++;
  if(dut.core.done_host356&&!dut.core.rows_done363)$fatal(1,"row return before DONE363");
  if(dut.core.output_phase&&(dut.core.source_we363||dut.core.row_valid363))$fatal(1,"row/source owner after phase363");
  if(dut.source_req363&&dut.host_req363)$fatal(1,"common executor owner overlap363");
  if(dut.core.row_valid363&&dut.core.encoder.state==dut.core.encoder.FETCH&&
     dut.core.row_data363[30:8]!={dut.core.encoder.generation,dut.core.encoder.block_id})$fatal(1,"row order363");
  if(dut.core.ram_b_we&&dut.core.ram_a_we&&dut.core.ram_b_addr==dut.core.ram_a_addr)$fatal(1,"row port collision363");
 end
 always @(posedge clk)if(!reset&&dut.core.ram_a_we)begin
  if(!((dut.core.ram_a_addr>=640&&dut.core.ram_a_addr<=705)||(dut.core.ram_a_addr>=800&&dut.core.ram_a_addr<=865)))$fatal(1,"row slot address363");
 end
 final $display("ROWS363 rows=%0d source=%0d host=%0d",rows363,bytes363,common363);
 task clear_output;''')
 p.write_text(s,newline='\n')
 for n in ('nes_rows363.py','probe_nes_rows363.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
