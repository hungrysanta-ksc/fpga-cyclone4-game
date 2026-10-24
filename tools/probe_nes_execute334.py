# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_execute332 as previous
from nes_execute334 import native,apply
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    if os.environ.get('NES334_ARM_ONLY')!='1':
        apply(d)
        p=d/'joint266_tb.sv';s=p.read_text()
        s=once(s,'''  if(dut.flow.state==dut.flow.MREAD313&&
     (dut.flow.data_command278||dut.flow.header[0]==7))$fatal(1,"original body reread");''','')
        # MREAD aliases PREAD in the shared reader. Count the actual encoded
        # reads rather than treating the old metadata state number as proof.
        s=once(s,' parameter integer ROM_WINDOW=0;', ''' integer original_reads334=0,read_sequence334=-1;
 always @(posedge host_clk)if(!reset&&!source_fault&&active263)begin
  if(read_sequence334!=dut.flow.packet_seq)begin read_sequence334=dut.flow.packet_seq;original_reads334=0;end
  if(dut.flow.state==dut.flow.PCAP&&(dut.flow.data_command278||dut.flow.header[0]==7))begin
   if(dut.flow.parser_address!=16+original_reads334)$fatal(1,"encoded payload reread334");
   original_reads334++;
  end
  if((dut.flow.state==dut.flow.SEAL&&dut.flow.data_command278)||dut.flow.state==dut.flow.TILEWAIT313)
   if(original_reads334!=dut.flow.plen)$fatal(1,"encoded payload count334");
 end
 always @(posedge clk)if(!reset&&!source_fault&&output_phase)begin
  if(dut.core.ram_a_we||dut.core.record_valid||dut.core.byte_valid||dut.core.record_active334)
   $fatal(1,"plan phase retains source write334");
  if(!dut.core.transport_empty)$fatal(1,"plan phase before source drain334");
 end
 parameter integer ROM_WINDOW=0;''')
        p.write_text(s,newline='\n')
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'      transfer(n267);', '      $fwrite(events261,"ARM_wire_start334,%0d,%0d,%0d,%0t\\n",f,tx[0],n267,$time);\n      transfer(n267);')
    s=once(s,' parameter integer ROM_WINDOW=0;', ''' always @(posedge clk)if(!reset&&active263&&tv263&&tr263&&ti263+1==tl263)
  $fwrite(events261,"tile_last334,%0d,%0d,%0d,%0t\\n",f,tk263,ts263,$time);
 reg [31:0] stage_token334=0,dma_token334=0;
 always @(posedge host_clk)if(!reset&&active263&&!source_fault)begin
  if(dut.flow.chunk_ready&&stage_token334!=dut.flow.chunk_token)begin
   stage_token334=dut.flow.chunk_token;
   $fwrite(events261,"stage_ready334,%0d,%0d,%0d,%0t\\n",f,dut.flow.owner,stage_token334,$time);
  end
  if(dut.flow.state==dut.flow.DMA&&dut.flow.chunk_ready&&dma_token334!=dut.flow.chunk_token)begin
   dma_token334=dut.flow.chunk_token;
   $fwrite(events261,"DMA_ready334,%0d,%0d,%0d,%0t\\n",f,dut.flow.owner,dma_token334,$time);
  end
 end
 parameter integer ROM_WINDOW=0;''')
    p.write_text(s,newline='\n')
    for n in ('nes_execute334.py','probe_nes_execute334.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
