# SPDX-License-Identifier: MIT
import shutil
import probe_nes_raster355 as previous
from nes_query356 import apply
from nes_delta231 import ROOT,sha
engine=previous.engine
old_prepare=engine.prepare
def prepare(*args,**kwargs):
 src,pins=old_prepare(*args,**kwargs);d=args[0];apply(d)
 p=d/'joint266_tb.sv';s=p.read_text().replace('dut.core.transport.publish','dut.core.transport.busy')
 s=s.replace('always @(posedge clk)begin\n  if(reset)published337','always @(posedge host_clk)begin\n  if(reset)published337').replace('always @(posedge clk)if(!reset&&dut.core.transport_crc_pending)','always @(posedge host_clk)if(!reset&&dut.core.transport_crc_pending)')
 a=s.index(' always @(posedge clk)if(!reset)begin\n  if(dut.core.encoder.a_we');b=s.index(' reg [7:0] tx',a)
 block=s[a:b].replace('posedge clk','posedge host_clk').replace('  if(query)queries++;\n','')
 x=block.index('  if(dut.core.encoder.state!=');y=block.index('  if(dut.core.record_valid&&dut.core.record_ready)',x)
 counters=block[x:y];block=block[:x]+block[y:]
 s=s[:a]+block+' always @(posedge clk)if(!reset)begin\n if(query)queries++;\n'+counters+' end\n'+s[b:]
 s=s.replace(' task clear_output;',r"""
 time query_start356;integer query_count356=0;
 always @(posedge host_clk)if(!reset)begin
  if(dut.core.query_host356&&dut.core.query_ready356)begin query_start356=$time;query_count356++;end
  if(dut.core.raw_response)$fwrite(events261,"query356,%0d,%0d,%0t,%0t\n",f,query_count356,query_start356,$time);
  if(dut.core.done_host356&&(dut.core.encoder.q_pending||dut.core.encoder.q_have))$fatal(1,"query not drained before input ACK356");
  if(dut.core.ram_a_we&&dut.core.ram_b_we&&dut.core.ram_a_addr==dut.core.ram_b_addr)$fatal(1,"phase port collision356");
 end
 task clear_output;""")
 p.write_text(s,newline='\n')
 for n in ('nes_query356.py','probe_nes_query356.py','nes_query355.sv'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
