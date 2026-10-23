# SPDX-License-Identifier: MIT
"""Pin-driven old/new reply and IRQ differential under changing live status."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha

TB=r'''
`timescale 1ns/1ps
module test;
 reg clk=0,reset=1,ss=1,sck=0,mosi=0;always #5 clk=~clk;
 reg [199:0] source_status=200'h0123456789abcdef0123456789abcdef0123456789abcdefabcd;
 reg [199:0] output_status=200'hfedcba9876543210fedcba9876543210fedcba98765432101234;
 reg [199:0] plan_status=200'h03872653872653872653872653872653872653872653872653;
 wire [112:0] a,b;wire ia,ib,ma,mb;integer checks=0,half=30;
 reference315 refdut(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .source_status(source_status),.output_status(output_status),.plan_status(plan_status),.progress_irq284(ia),.progress_mode284(ma),.request_crc_enable(1'b1),.link(a));
 nes_spi270 dut(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .source_status(source_status),.output_status(output_status),.plan_status(plan_status),.progress_irq284(ib),.progress_mode284(mb),.request_crc_enable(1'b1),.link(b));
 always @(negedge clk)if(!reset)begin
  if({a,ia,ma}!=={b,ib,mb})$fatal(1,"reply/link/IRQ mismatch count %0d command %h A%h B%h",refdut.count,refdut.command,a,b);
  checks++;
 end
 task byte315(input [7:0] v,input integer abortbit);
 begin
  for(integer bitn=7;bitn>=0;bitn--)begin
   mosi=v[bitn];#(half);sck=1;#(half);sck=0;
   if(bitn==abortbit)begin ss=1;#200;return;end
  end
 end endtask
 task transfer315(input [7:0] command,input integer size,input integer abortbit);
 begin
  ss=0;#100;byte315(command,-1);
  for(integer i=1;i<size;i++)begin
   // Change all live status while the immutable response is transmitted.
   source_status={source_status[191:0],8'(i)};
   output_status={output_status[191:0],8'(i^8'ha5)};
   plan_status={plan_status[191:0],8'(i^8'h5a)};
   byte315(8'(i*37+command),i==3?abortbit:-1);
   if(ss)break;
  end
  #100;ss=1;#500;
 end endtask
 initial begin
  #200;reset=0;#200;
  for(integer speed=0;speed<2;speed++)begin
   half=speed==0?30:200;
   transfer315('hd0,8,-1);transfer315('hd2,8,-1);transfer315('hd3,8,-1);
   transfer315('he0,26,-1);transfer315('he2,14,-1);transfer315('he8,14,-1);
   transfer315('he1,259,-1);transfer315('he9,80,-1);transfer315('hea,7,-1);
   transfer315('hd4,8,-1);transfer315('hd5,8,-1);transfer315('hff,32,-1);
   for(integer bitn=0;bitn<8;bitn++)transfer315('he0,26,bitn);
  end
  reset=1;#100;reset=0;#100;transfer315('he2,14,-1);
  $display("PASS REPLY315 41 transfers 2 speeds 16 partial-byte aborts checks=%0d",checks);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);shutil.copyfile(a.source/'nes_spi270.sv',d/'nes_spi270.sv')
    (d/'reference.sv').write_text((a.reference/'nes_spi270.sv').read_text().replace('module nes_spi270(', 'module reference315('),newline='\n')
    (d/'test.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    for tool,args in [('vlib',['work']),('vlog',['-sv','nes_spi270.sv','reference.sv','test.sv']),('vsim',['-c','test','-do','run -all;quit -f'])]:
        with (d/(tool+'.log')).open('wb') as log:r=subprocess.run([q/(tool+'.exe'),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        raw=(d/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and '** Error' not in raw and '** Fatal' not in raw,raw[-3000:]
    assert 'PASS REPLY315' in raw
    result=dict(passed=True,transfers=41,partial_byte_aborts=16,scope='Two simulated SPI rates; no physical maximum-frequency claim',actual_inputs={n:sha(d/n) for n in ('nes_spi270.sv','reference.sv','test.sv')})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
