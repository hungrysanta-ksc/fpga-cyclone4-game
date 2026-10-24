# SPDX-License-Identifier: MIT
"""Passive read/receipt port audit of unchanged332 RTL with334 ARM."""
import os,shutil
os.environ['NES334_ARM_ONLY']='1'
os.environ['NES332_ARM_ONLY']='0'
os.environ['NES331_ARM_ONLY']='0'
os.environ['NES330_MAP']='1'
import probe_nes_execute334 as previous
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' parameter integer ROM_WINDOW=0;',r'''
 reg dma_seen335=0,served335=0;
 reg [31:0] token335=0;
 integer frame335=-1;
 integer state_ticks335[0:63];
 always @(posedge host_clk)if(!reset&&active263)begin
  if(frame335!=f)begin
   frame335=f;dma_seen335=0;served335=0;
   for(integer j=0;j<64;j++)state_ticks335[j]=0;
  end
  state_ticks335[dut.core.validator.state]++;
  if(dut.flow.state!=dut.flow.DMA||!dut.flow.chunk_ready)dma_seen335=0;
  if(dut.flow.state==dut.flow.DMA&&dut.flow.chunk_ready&&(!dma_seen335||token335!=dut.flow.chunk_token))begin
   dma_seen335=1;token335=dut.flow.chunk_token;
   $fwrite(events261,"desc335,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,
    token335,dut.flow.header[0],dut.flow.header[1],dut.flow.startpos,dut.flow.outlen,dut.flow.chunk_length,
    dut.flow.identity[48],dut.flow.receipt_first282,dut.flow.receipt_limit287,dut.flow.zero325,$time);
  end
  if(bus_read)served335=0;
  if(!served335&&!bus_read&&bus_write&&bus_valid&&bus_address>=24'h400800&&bus_address<24'h401800)begin
   served335=1;
   $fwrite(events261,"byte335,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.chunk_token,bus_address-24'h400800,bus_out,$time);
  end
  if(!dut.flow.invalidate_banks&&dut.flow.rs&&!dut.flow.rp&&dut.flow.ap>=24'h400800&&dut.flow.ap<24'h401800)
   $fwrite(events261,"read335,%0d,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.chunk_token,dut.flow.ap-24'h400800,dut.flow.read_count,dut.flow.chunk_length,$time);
  if(dut.flow.consume_write&&dut.flow.good_consume)
   $fwrite(events261,"ack335,%0d,%0d,%0t\n",f,dut.flow.chunk_token,$time);
  if(dut.core.validator.v_range_valid&&dut.core.validator.v_ready)
   $fwrite(events261,"range335,%0d,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.chunk_token,dut.core.validator.v_map_range,dut.core.validator.v_first,dut.core.validator.range_end283,$time);
  if(dut.core.validator.state==dut.core.validator.V_RREAD||dut.core.validator.state==dut.core.validator.V_RWRITE||
     dut.core.validator.state==dut.core.validator.V_PREAD||dut.core.validator.state==dut.core.validator.V_PWRITE)
   $fwrite(events261,"port335,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,dut.flow.chunk_token,
    dut.core.validator.state,dut.core.validator.ram_addr,dut.core.validator.ram_we,dut.core.validator.ram_w,
    dut.core.validator.v_bit_at,dut.core.validator.v_end283,$time);
  if(dut.flow.canonical_write313)
   $fwrite(events261,"expected335,%0d,%0d,%0d,%0t\n",f,dut.flow.canonical_address313,dut.flow.held,$time);
 end
 parameter integer ROM_WINDOW=0;''')
    s=once(s,'   $fwrite(events261,"frame_done,', '''   for(integer j335=0;j335<64;j335++)if(state_ticks335[j335])
    $fwrite(events261,"state335,%0d,%0d,%0d\\n",f,j335,state_ticks335[j335]);
   $fwrite(events261,"frame_done,''')
    p.write_text(s,newline='\n')
    shutil.copyfile(ROOT/'tools/probe_nes_receipt335.py',d/'probe_nes_receipt335.py');pins['probe_nes_receipt335.py']=sha(d/'probe_nes_receipt335.py')
    return src,pins


engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
