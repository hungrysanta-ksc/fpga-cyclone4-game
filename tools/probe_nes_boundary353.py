# SPDX-License-Identifier: MIT
"""Passive clock/port ownership trace on338 RTL and352 ARM."""
import shutil
import probe_nes_raw352 as old
from nes_delta231 import ROOT,sha,once
engine=old.engine
previous=engine.prepare
OBSERVER=r'''
 integer trace353,vs353=-1,hs353=-1,phase353=-1;
 initial begin
  trace353=$fopen("boundary353.csv","w");
  $fwrite(trace353,"domain,frame,time,state,phase,query,response,addr,we,data,plan_zero,plan_step,cursor,byte_fire,crc_pending,queue_write,queue_addr\n");
 end
 always @(posedge clk)if(!reset)begin
  if(query||response||dut.core.ram_a_we||plan_zero319||plan_step319||
     dut.core.encoder.byte_valid&&dut.core.encoder.byte_ready||phase353!=dut.core.output_phase)begin
   $fwrite(trace353,"N,%0d,%0t,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,0,0\n",
    f,$time,dut.core.encoder.state,dut.core.output_phase,query,response,dut.core.ram_a_addr,
    dut.core.ram_a_we,dut.core.ram_a_w,plan_zero319,plan_step319,plan_cursor319,
    dut.core.encoder.byte_valid&&dut.core.encoder.byte_ready,dut.core.transport.crc_pending);
  end
  if(dut.core.ram_a_we&&dut.core.output_phase)$fatal(1,"source RAM write during output phase353");
  if((plan_zero319||plan_step319)&&!dut.core.output_phase)$fatal(1,"plan cursor outside output phase353");
  phase353=dut.core.output_phase;
 end
 always @(posedge host_clk)if(!reset)begin
  if(dut.core.ram_b_we||dut.flow.queue.write312||vs353!=dut.core.validator.state||hs353!=dut.flow.state)
   $fwrite(trace353,"H,%0d,%0t,%0d,%0d,0,0,%0d,%0d,%0d,0,0,0,0,0,%0d,%0d\n",
    f,$time,dut.flow.state,dut.core.output_phase,dut.core.ram_b_addr,dut.core.ram_b_we,
    dut.core.ram_b_w,dut.flow.queue.write312,dut.flow.queue.write_address312);
  vs353=dut.core.validator.state;hs353=dut.flow.state;
 end
'''
def prepare(*a,**k):
    src,pins=previous(*a,**k);d=a[0]
    p=d/'joint266_tb.sv';p.write_text(once(p.read_text(),'endmodule',OBSERVER+'\nendmodule'),newline='\n')
    shutil.copyfile(ROOT/'tools/probe_nes_boundary353.py',d/'probe_nes_boundary353.py');pins['probe_nes_boundary353.py']=sha(d/'probe_nes_boundary353.py')
    return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
