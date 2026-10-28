# SPDX-License-Identifier: MIT
"""Real SPI/dual-clock source storage credits, invalid ACKs and STOP."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_refill267 import run
TB=r'''`timescale 1ns/1ps
module credit371_tb;
 reg h=0,n=0;always #5.952380952 h=~h;always #22.727272727 n=~n;
 reg reset=1,abortq=0,rv=0,bv=0,last=0;reg [7:0] bd=0;
 reg ss=1,sck=0,mosi=0;wire miso,selected,rr,br,ack,accept,sf,hf,emptyq,cp,take;
 wire [15:0] ag,previous;wire [7:0] cb;wire [113:0] link;wire [199:0] status;
 integer acks=0,cases=0;reg [7:0] tx[0:31],rx[0:31];
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);reg [7:0] c;begin c=c0^b;for(integer j=0;j<8;j++)c=c[7]?(c<<1)^7:c<<1;return c;end endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);reg [15:0] c;begin c=c0^{b,8'd0};for(integer j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction
 nes_spi270 front(.clk(h),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(status),.output_status(200'd0),.plan_status(200'd0),.request_crc_enable(take),.queue_admit319(1'b1),.plan_admit319(1'b1),.link(link),.progress_irq284(),.progress_mode284(),.source_mode367());
 nes_transport257 #(.SPLIT_CREDIT371(1)) dut(.record_last319(last),.link270(link),.status270(status),.crc_take270(take),
  .crc_result(c16(previous,cb)),.crc_pending(cp),.crc_previous(previous),.crc_byte(cb),.frame_generation(16'd3),
  .src_clk(n),.host_clk(h),.reset(reset),.abort_source(abortq),.record_valid(rv),.record_ready(rr),.record_length(8'd8),.record_flush(1'b1),
  .byte_valid(bv),.byte_ready(br),.byte_data(bd),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso),
  .ack_valid(ack),.ack_ready(1'b1),.ack_accept(accept),.ack_generation(ag),.source_fault(sf),.host_fault(hf),.source_empty(emptyq));
 always @(posedge n)if(!reset&&ack)begin if(!accept||ag!=3)$fatal(1,"input ACK identity");acks++;end
 task write_block(input [7:0] base);begin
  @(negedge n);rv=1;while(!rr)@(negedge n);@(negedge n);rv=0;
  for(integer i=0;i<8;i++)begin
   bd=base+i;bv=1;last=i==7;while(!br)@(negedge n);@(negedge n);bv=0;last=0;@(negedge n);
  end
 end endtask
 task setup;begin
  reset=1;abortq=0;rv=0;bv=0;last=0;ss=1;sck=0;#1000;reset=0;#2000;acks=0;
  write_block(8'h30);write_block(8'h40);wait(&dut.block_valid);#1000;
 end endtask
 task packet(input [7:0] command,input integer token,input integer generation,input integer flags);reg [7:0] c;begin
  for(integer i=0;i<32;i++)tx[i]=0;
  tx[0]=command;tx[1]=token>>8;tx[2]=token;tx[3]=generation;tx[4]=generation>>8;tx[5]=flags;
  c=0;for(integer i=0;i<6;i++)c=c8(c,tx[i]);tx[6]=c;tx[7]=8'ha5;
 end endtask
 task send(input integer count);begin
  #2000;ss=0;#2000;
  for(integer i=0;i<count;i++)begin rx[i]=0;for(integer b=7;b>=0;b--)begin
   mosi=tx[i][b];#190.476190476;sck=1;rx[i][b]=selected?miso:0;#190.476190476;sck=0;
  end end
  #2000;ss=1;#8000;
 end endtask
 task read_block(input integer token,input [7:0] base);reg [7:0] c;reg [15:0] cr;begin
  packet(8'hd4,token,3,0);send(23);
  c=0;for(integer i=8;i<12;i++)c=c8(c,rx[i]);cr=16'hffff;
  if(hf||rx[9]!=8||rx[12]!=c)$fatal(1,"source header");
  for(integer i=0;i<8;i++)begin if(rx[13+i]!==8'(base+i))$fatal(1,"source payload");cr=c16(cr,rx[13+i]);end
  if({rx[21],rx[22]}!=cr)$fatal(1,"source CRC");
 end endtask
 initial begin
  setup();read_block(0,8'h30);packet(8'hd5,0,3,1);send(8);
  if(hf||acks||dut.token!=1||dut.ack_pending)$fatal(1,"storage credit became ACK");
  read_block(1,8'h40);packet(8'hd5,1,3,3);send(8);if(hf||acks!=1||dut.token!=2)$fatal(1,"final input ACK");cases++;
  for(integer bad=0;bad<5;bad++)begin
   setup();read_block(0,8'h30);
   case(bad)0:packet(8'hd5,0,3,2);1:packet(8'hd5,1,3,1);2:packet(8'hd5,0,4,1);3:packet(8'hd5,0,3,3);4:packet(8'hd4,0,3,1);endcase
   send(bad==4?13:8);if(!hf||acks||dut.token!=0)$fatal(1,"bad credit accepted %0d",bad);cases++;
  end
  for(integer cut=1;cut<8;cut++)begin setup();read_block(0,8'h30);packet(8'hd5,0,3,1);send(cut);
   if(!hf||acks||dut.token!=0)$fatal(1,"truncated credit %0d",cut);cases++;
  end
  setup();read_block(0,8'h30);packet(8'hd5,0,3,1);send(8);packet(8'hd5,1,3,1);send(8);
  if(!hf||acks||dut.token!=1)$fatal(1,"credit without read");cases++;
  setup();read_block(0,8'h30);abortq=1;#2000;packet(8'hd5,0,3,3);send(8);abortq=0;#2000;
  if(acks||!sf||!hf)$fatal(1,"ACK after STOP");cases++;
  $display("PASS CREDIT371 cases=%0d",cases);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout credit371");end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-source368/map01';new=BASE/'repository-nes-milestone/src/fpga/nes_ingress371'
 names=['nes_transport257.sv','nes_spi270.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
 for n in names:shutil.copyfile((new if (new/n).exists() else old)/n,d/n)
 (d/'credit371_tb.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'credit371_tb.sv'],d,'vlog')
 raw=run(q/'vsim.exe',['-c','work.credit371_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);assert 'PASS CREDIT371 cases=15' in raw
 (d/'result.json').write_text(json.dumps(dict(passed=True,cases=15,pins={str(d/n):sha(d/n) for n in names+['credit371_tb.sv']}),indent=2)+'\n');print('PASS CREDIT371 cases=15')
if __name__=='__main__':main()
