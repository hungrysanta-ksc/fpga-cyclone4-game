# SPDX-License-Identifier: MIT
"""Pin-level response rotation, immutable identity and IRQ reference tests."""
import argparse,json,shutil
from pathlib import Path
from probe_nes_refill267 import run
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);shutil.copyfile(a.source/'nes_spi270.sv',d/'nes_spi270.sv')
    tb=r'''
`timescale 1ns/1ps
module spi331_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ss=1,sck=0,mosi=0;
 reg [199:0] source_status=0,output_status=0,plan_status=0;
 wire [113:0] link;wire irq,mode;
 nes_spi270 dut(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
 .source_status(source_status),.output_status(output_status),.plan_status(plan_status),
 .progress_irq284(irq),.progress_mode284(mode),.request_crc_enable(1'b0),
 .queue_admit319(1'b1),.plan_admit319(1'b1),.link(link));
 function automatic [7:0] crc(input [7:0] c0,b);
  reg [7:0] c;begin c=c0^b;for(integer k=0;k<8;k++)c=c[7]?(c<<1)^7:c<<1;crc=c;end
 endfunction
 task octet(input [7:0] tx,output reg [7:0] rx);
  begin for(integer b=7;b>=0;b--)begin mosi=tx[b];#190;sck=1;rx[b]=link[107];#190;sck=0;end end
 endtask
 task transaction(input [7:0] cmd,input integer mutation);
  reg [199:0] expected;reg [7:0] rx,c,want;integer n;
  begin
   for(integer b=0;b<25;b++)begin source_status[b*8+:8]=$random;output_status[b*8+:8]=$random;plan_status[b*8+:8]=$random;end
   if(cmd==8'he0)begin expected={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],output_status[127:96],output_status[63:8],16'd0};n=24;end
   else if(cmd==8'hd0||cmd==8'hd2||cmd==8'hd3)begin expected={source_status[183:0],16'd0};n=7;end
   else begin expected={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],104'd0};n=13;end
   ss=0;#200;octet(cmd,rx);#100;
   if(mutation==1)output_status[199:184]=output_status[199:184]+1;
   if(mutation==2)output_status[127:96]=~output_status[127:96];
   if(mutation==3)output_status[167:152]=output_status[167:152]+1;
   if(mutation==4)output_status[175]=~output_status[175];
   if(mutation==5)plan_status[167:160]=~plan_status[167:160];
   if(mutation==6)output_status[151:136]=output_status[151:136]+1;
   c=0;
   for(integer i=0;i<n;i++)begin
    octet(0,rx);want=i==n-1?c:expected[199-i*8-:8];
    if(rx!==want)$fatal(1,"response cmd=%x mutation=%0d byte=%0d got=%x want=%x",cmd,mutation,i,rx,want);
    if(i<n-1)c=crc(c,rx);
    if(cmd==8'he2||cmd==8'he1||cmd==8'he9||cmd==8'he8)
     if(irq!==(mutation==1||mutation>=4))$fatal(1,"IRQ reference moved while serializing");
   end
   ss=1;#400;
  end
 endtask
 initial begin
  #100;reset=0;#200;
  for(integer trial=0;trial<7;trial++)begin
   transaction(8'he0,trial);transaction(8'he2,trial);transaction(8'he1,trial);transaction(8'he9,trial);transaction(8'he8,trial);
   transaction(8'hd0,trial);transaction(8'hd2,trial);transaction(8'hd3,trial);
  end
  // Reset while a response is live: no stale wake or residual response survives.
  ss=0;#400;begin reg [7:0] rx;octet(8'he2,rx);reset=1;#100;ss=1;reset=0;#400;
   if(irq||dut.snapshot||dut.status_length)$fatal(1,"reset retains response");end
  transaction(8'he0,1);transaction(8'he2,1);
  $display("PASS SPI331 58 responses CRC immutable_identity stable_IRQ fault_wake reset");$finish;
 end
endmodule
'''
    (d/'spi331_tb.sv').write_text(tb,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_spi270.sv','spi331_tb.sv'],d,'vlog')
    raw=run(q/'vsim.exe',['-c','work.spi331_tb','-do','run -all;quit -f'],d,'vsim',60)
    assert 'PASS SPI331' in raw
    (d/'result.json').write_text(json.dumps(dict(passed=True,RTL_sha256=sha(d/'nes_spi270.sv'),tb_sha256=sha(d/'spi331_tb.sv'),log_sha256=sha(d/'vsim.log')))+'\n',newline='\n')


if __name__=='__main__':main()
