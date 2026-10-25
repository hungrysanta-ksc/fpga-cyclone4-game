# SPDX-License-Identifier: MIT
"""Passive queue/host RAM port observation on unchanged338 RTL/336 ARM."""
import shutil
import probe_nes_ingress338 as previous
from nes_delta231 import ROOT, sha, once
engine=previous.engine
old=engine.prepare

OBSERVER=r'''
 integer port350, ps350=-1, pr350=-1, pa350=-1, pc350=-1;
 reg lastreset350=1, sample350=0;
 reg [7:0] expected350;
 reg [9:0] prevaddr350;
 wire req350=dut.flow.state==dut.flow.HLOAD315||dut.flow.state==dut.flow.PREAD||
  dut.flow.state==dut.flow.DREAD||dut.flow.state==dut.flow.MREAD313||dut.flow.canonical_read313;
 wire cap350=dut.flow.record_valid312||dut.flow.state==dut.flow.PCAP||
  dut.flow.state==dut.flow.DCAP||dut.flow.state==dut.flow.MCAP313;
 initial begin
  port350=$fopen("ports350.csv","w");
  $fwrite(port350,"frame,time,state,op,parser,at,read_addr,read_data,request,capture,expected_write,write_data,ingress_write,ingress_addr,accepted,retired,consumed,range_ready,reset,fault,previous_addr,validator_state\n");
 end
 always @(posedge host_clk)begin
  if(port350&&active263)begin
   if(sample350&&cap350&&!dut.flow.rst&&!dut.flow.fault&&dut.flow.qdata!==expected350)
    $fatal(1,"queue RAM response ownership350 addr=%0d",prevaddr350);
   if(dut.flow.queue.write312&&dut.flow.canonical_write313&&
      dut.flow.queue.write_address312==dut.flow.queue.read_address312)
    $fatal(1,"queue dual port write collision350");
   if(req350||cap350||dut.flow.canonical_write313||dut.flow.queue.write312||
      ps350!=dut.flow.state||pr350!=dut.flow.queue.retired||pa350!=dut.flow.queue.accepted||
      pc350!=dut.flow.queue.consumed312||lastreset350!=dut.flow.rst)
    $fwrite(port350,"%0d,%0t,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",
     f,$time,dut.flow.state,dut.flow.header[0],dut.flow.parser_address,dut.flow.at,
     dut.flow.queue.read_address312,dut.flow.qdata,req350,cap350,dut.flow.canonical_write313,dut.flow.held,
     dut.flow.queue.write312,dut.flow.queue.write_address312,dut.flow.queue.accepted,dut.flow.queue.retired,
     dut.flow.queue.consumed312,dut.flow.range_ready,dut.flow.rst,dut.flow.fault,prevaddr350,dut.core.validator.state);
  end
  expected350=dut.flow.queue.buffer[dut.flow.queue.read_address312];
  prevaddr350=dut.flow.queue.read_address312;sample350=1;
  ps350=dut.flow.state;pr350=dut.flow.queue.retired;pa350=dut.flow.queue.accepted;
  pc350=dut.flow.queue.consumed312;lastreset350=dut.flow.rst;
 end
'''

def prepare(*a,**k):
    src,pins=old(*a,**k);d=a[0]
    p=d/'joint266_tb.sv';p.write_text(once(p.read_text(),'endmodule',OBSERVER+'\nendmodule'),newline='\n')
    shutil.copyfile(ROOT/'tools/probe_nes_port350.py',d/'probe_nes_port350.py')
    pins['probe_nes_port350.py']=sha(d/'probe_nes_port350.py')
    return src,pins

engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
