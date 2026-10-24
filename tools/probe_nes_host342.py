# SPDX-License-Identifier: MIT
"""Host reader/progress replacement plus frontier; source remains selected338."""
import probe_nes_frontier342 as previous
from nes_runs342 import host
from nes_delta231 import once
engine=previous.engine
prepare0=engine.prepare

def prepare(*a,**k):
 src,pins=prepare0(*a,**k);d=a[0];host(d)
 p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,"""  if(dut.flow.state==dut.flow.MREAD313&&
     (dut.flow.data_command278||dut.flow.header[0]==7))$fatal(1,"original body reread");""",'')
 s=once(s,' parameter integer ROM_WINDOW=0;',""" integer original_reads342=0,read_sequence342=-1;
 always @(posedge host_clk)if(!reset&&!source_fault&&active263)begin
  if(read_sequence342!=dut.flow.packet_seq)begin read_sequence342=dut.flow.packet_seq;original_reads342=0;end
  if(dut.flow.state==dut.flow.PCAP&&(dut.flow.data_command278||dut.flow.header[0]==7))begin
   if(dut.flow.parser_address!=16+original_reads342)$fatal(1,"encoded payload reread342");
   original_reads342++;
  end
  if((dut.flow.state==dut.flow.SEAL&&dut.flow.data_command278)||dut.flow.state==dut.flow.TILEWAIT313)
   if(original_reads342!=dut.flow.plen)$fatal(1,"encoded payload count342");
 end
 parameter integer ROM_WINDOW=0;""")
 p.write_text(s,newline='\n');return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
