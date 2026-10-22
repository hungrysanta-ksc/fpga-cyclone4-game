# SPDX-License-Identifier: MIT
"""Shared SPI: interleaving, immutable snapshots, wrap, CRC and partial SS."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import sha
from probe_nes_joint266 import run

TB=r'''
`timescale 1ns/1ps
module spi270_tb;
 reg clk=0;always #5.952381 clk=~clk;
 reg reset=1,ss=1,sck=0,mosi=0,retire=0;reg [127:0] progress=128'h0102030405060708090a0b0c0d0e0f10;
 wire [48:0] link;wire [183:0] qs,ssource,ps;wire qc,sc,pc,qsel,ssel,psel,qm,sm,pm,qf,sf,hf,pf,qr;
 wire [8:0] qlength;wire av,aa;wire [15:0] ag;wire pw,pseal;wire [9:0] plen;wire [4:0] pn;wire [15:0] pcrc;
 integer checks=0,planwrites=0,planseals=0;reg mutate=0;reg [7:0] tx[0:1023],rx[0:1023];reg [15:0] c;
 wire miso=qsel?qm:ssel?sm:psel?pm:1'b0;
 nes_spi270 common(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(ssource),.output_status(qs),.plan_status(ps),.request_crc_enable(sc||pc),.link(link));
 nes_queue260 queue(.link270(link),.status270(qs),.crc_take270(qc),.progress_status(progress),.parser_retire(retire),
 .clk(clk),.reset(reset),.enable(1'b1),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(qsel),.miso(qm),
 .sn_address(8'd0),.sn_data(),.packet_ready(qr),.packet_length(qlength),.fault(qf));
 nes_transport257 source(.link270(link),.status270(ssource),.crc_take270(sc),.crc_result(16'd0),.crc_pending(),.crc_previous(),.crc_byte(),
 .src_clk(clk),.host_clk(clk),.reset(reset),.abort_source(1'b0),.record_valid(1'b0),.record_ready(),.record_length(8'd0),.record_flush(1'b0),
 .byte_valid(1'b0),.byte_ready(),.byte_data(8'd0),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(ssel),.miso(sm),
 .ack_valid(av),.ack_ready(1'b0),.ack_accept(aa),.ack_generation(ag),.source_fault(sf),.host_fault(hf),.source_empty());
 nes_plan_spi200 plan(.link270(link),.status270(ps),.crc_take270(pc),.clk(clk),.reset(reset),.enable(1'b1),.stop(1'b0),.source_fault(1'b0),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(psel),.miso(pm),.fault(pf),.plan_idle(1'b1),.plan_ready(1'b1),.plan_write(pw),.plan_data(),
 .plan_seal(pseal),.plan_length(plen),.plan_plans(pn),.plan_crc(pcrc),.retire_done(1'b0),.retire(),.end_generation(16'd1),
 .chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),.end_sealed(1'b0));
 always @(posedge clk)begin
  if((qsel&&ssel)||(qsel&&psel)||(ssel&&psel))$fatal(1,"multiple SPI owners");
  if(pw)planwrites++;if(pseal)planseals++;
 end
 function automatic [7:0] crc8(input [7:0] x,input [7:0] b);
  reg [7:0] v;begin v=x^b;for(integer j=0;j<8;j++)v=v[7]?(v<<1)^8'h07:v<<1;return v;end
 endfunction
 function automatic [15:0] crc16(input [15:0] x,input [7:0] b);
  reg [15:0] v;begin v=x^{b,8'd0};for(integer j=0;j<8;j++)v=v[15]?(v<<1)^16'h1021:v<<1;return v;end
 endfunction
 task clear;
 begin ss=1;sck=0;mosi=0;reset=1;retire=0;repeat(8)@(negedge clk);reset=0;repeat(40)@(negedge clk);for(integer i=0;i<1024;i++)tx[i]=0;end endtask
 task transfer(input integer n,input integer extra_bits);
 begin
  ss=0;#400;
  for(integer j=0;j<n;j++)begin
   rx[j]=0;
   for(integer i=7;i>=0;i--)begin mosi=tx[j][i];#190.476;sck=1;rx[j][i]=miso;#190.476;sck=0;end
   if(mutate&&j==4)progress=~progress;
  end
  for(integer i=0;i<extra_bits;i++)begin mosi=1;#190.476;sck=1;#190.476;sck=0;end
  #400;ss=1;#1000;
 end endtask
 task check_status(input integer n,input [7:0] marker);
 reg [7:0] crc;begin crc=0;for(integer i=1;i<n-1;i++)crc=crc8(crc,rx[i]);
 if(rx[1]!==marker||rx[n-1]!==crc)$fatal(1,"status CRC n%0d marker%h crc%h expected%h",n,rx[1],rx[n-1],crc);checks++;end endtask
 task dcommand(input [7:0] op);
 begin tx[0]=op;tx[1]=0;tx[2]=0;tx[3]=0;tx[4]=0;tx[5]=255;tx[6]=0;
 for(integer i=0;i<6;i++)tx[6]=crc8(tx[6],tx[i]);tx[7]=8'ha5;end endtask
 task packet;
 begin for(integer i=0;i<19;i++)tx[i]=0;tx[0]=8'he1;c=16'hffff;for(integer i=0;i<17;i++)c=crc16(c,tx[i]);tx[17]=c[15:8];tx[18]=c[7:0];end endtask
 initial begin
  clear();dcommand(8'hd0);transfer(8,0);check_status(8,8'hd8);
  tx[0]=8'he2;transfer(9,0);check_status(9,8'hf9);if(rx[7]!=1)$fatal(1,"short phase");
  tx[0]=8'he8;transfer(20,0);check_status(20,8'hd7);
  tx[0]=8'he0;mutate=1;transfer(24,0);mutate=0;check_status(24,8'hf8);
  for(integer i=7;i<23;i++)if(rx[i]!==i-6)$fatal(1,"snapshot changed during transfer");checks++;
  dcommand(8'hd3);tx[2]=8'h12;tx[3]=8'h34;tx[4]=1;tx[5]=254;tx[6]=0;
  for(integer i=0;i<6;i++)tx[6]=crc8(tx[6],tx[i]);transfer(8,0);repeat(20)@(negedge clk);
  if(!av||!aa||ag!=16'h1234||hf||sf)$fatal(1,"source shared request CRC/ACK");checks++;
  clear();@(negedge clk);queue.accepted=16'hfffe;queue.retired=16'hfffe;
  repeat(4)begin packet();transfer(19,0);end
  tx[0]=8'he2;transfer(9,0);check_status(9,8'hf9);
  if(qf||queue.accepted!=2||queue.retired!=16'hfffe||rx[2]!=5)$fatal(1,"credit wrap/full");checks++;
  repeat(4)begin @(negedge clk);retire=1;@(negedge clk);retire=0;end
  if(queue.retired!=2||qr||qf)$fatal(1,"retire wrap");checks++;
  for(integer n=8;n<=10;n=n+2)begin clear();tx[0]=8'he2;transfer(n,0);if(!qf||queue.accepted)$fatal(1,"bad short length");checks++;end
  clear();tx[0]=8'he2;transfer(9,1);if(!qf)$fatal(1,"partial short bit");checks++;
  clear();packet();tx[18]^=1;transfer(19,0);if(!qf||queue.accepted)$fatal(1,"output CRC published");checks++;
  clear();repeat(4)begin packet();transfer(19,0);end
  packet();tx[1]=8'h99;c=16'hffff;for(integer i=0;i<17;i++)c=crc16(c,tx[i]);tx[17]=c[15:8];tx[18]=c[7:0];transfer(19,0);
  if(!qf||queue.accepted!=4||queue.buffer[0]!==0)$fatal(1,"full queue overwritten");checks++;
  clear();dcommand(8'hd0);tx[6]^=1;transfer(8,0);if(!hf)$fatal(1,"source CRC accepted");checks++;
  clear();dcommand(8'hd2);transfer(8,0);if(!hf||source.token||source.pop0||source.pop1)$fatal(1,"unread source POP");checks++;
  clear();tx[0]=8'he9;tx[1]=3;tx[2]=0;tx[3]=1;tx[4]=8'h83;tx[5]=1;tx[6]=0;
  c=16'hffff;for(integer i=4;i<7;i++)c=crc16(c,tx[i]);tx[7]=c[15:8];tx[8]=c[7:0];tx[9]=0;
  for(integer i=0;i<9;i++)tx[9]=crc8(tx[9],tx[i]);tx[10]=8'ha5;transfer(11,0);
  if(pf||plen!=3||pn!=1||pcrc!=c||planseals!=1||planwrites!=3)$fatal(1,"plan shared CRC");checks++;
  tx[9]^=1;transfer(11,0);if(!pf||planseals!=1)$fatal(1,"bad plan CRC sealed");checks++;
  // Raw endpoint limit, not a claim that these bytes form a semantic plan.
  clear();planwrites=0;planseals=0;tx[0]=8'he9;tx[1]=0;tx[2]=2;tx[3]=16;c=16'hffff;
  for(integer i=0;i<512;i++)begin tx[i+4]=i[7:0];c=crc16(c,tx[i+4]);end
  tx[516]=c[15:8];tx[517]=c[7:0];tx[518]=0;for(integer i=0;i<518;i++)tx[518]=crc8(tx[518],tx[i]);tx[519]=8'ha5;
  transfer(520,0);if(pf||plen!=512||pn!=16||pcrc!=c||planwrites!=512||planseals!=1)$fatal(1,"10-bit shared count maximum E9");checks++;
  clear();packet();transfer(7,3);if(!qf||queue.accepted)$fatal(1,"partial packet published");checks++;
  clear();tx[0]=8'he2;transfer(9,0);check_status(9,8'hf9);if(qf||hf||pf)$fatal(1,"reset rearm");
  $display("PASS SPI270 checks=%0d",checks);$finish;
 end
 initial begin #5000000;$fatal(1,"SPI guard timeout");end
endmodule
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 names=['nes_spi270.sv','nes_queue260.sv','nes_transport257.sv','nes_plan_spi200.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
 for n in names:shutil.copyfile(a.source/n,d/n)
 (d/'spi270_tb.sv').write_text(TB,encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/Path(__file__).name)
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*names,'spi270_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','work.spi270_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim');assert 'PASS SPI270' in log
 result=dict(passed=True,scope=__doc__,rtl_hashes={n:sha(d/n) for n in names},TB_sha256=sha(d/'spi270_tb.sv'),log=[l for l in log.splitlines() if 'PASS SPI270' in l]);(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['log'])

if __name__=='__main__':main()
