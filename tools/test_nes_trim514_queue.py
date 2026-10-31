# SPDX-License-Identifier: MIT
"""Drive the board's E1 queue over SPI with the exact ARM ordinary packets and checked acknowledgments."""
import argparse
import binascii
import json
import shutil
import subprocess
from pathlib import Path
from nes_raw506 import sha

TB=r"""module trim514_queue_tb;
 reg clk=0,reset=1,ss=1,sck=0,mosi=0,wr=0,pub=0;
 reg [7:0] addr=0,ack=0;reg [3:0] idx=0;
 wire [7:0] data; wire [8:0] len;wire ready,fault;
 always #6 clk=~clk;
 nes_sink_spi165 dut(clk,reset,1'b1,ss,sck,mosi,,,addr,data,ready,len,wr,idx,ack,pub,fault);
 reg [7:0] stream[0:@LAST@];integer starts[0:3],sizes[0:3],position=0,accepted=0,retired=0,n,i,j,p,corrupt=0,partials=0;
 task send_byte(input [7:0] val);integer k;begin
  for(k=7;k>=0;k=k-1)begin mosi=val[k];#96;sck=1;#192;sck=0;#96;end
 end endtask
 task send_head;begin
  n=stream[position]+256*stream[position+1];position=position+2;
  starts[accepted%4]=position;sizes[accepted%4]=n;
  ss=0;#192;send_byte(8'he1);
  for(j=0;j<n+2;j=j+1)send_byte(stream[position+j] ^ ((corrupt!=0 && j==n+1)?1:0));
  ss=1;#192;position=position+n+2;accepted=accepted+1;
 end endtask
 task consume_head;begin
  p=starts[retired%4];n=sizes[retired%4];
  if(!ready || fault || len!=n)$fatal(1,"head length");
  if(stream[p]==10)partials=partials+1;
  for(i=0;i<n;i=i+1)begin @(negedge clk);addr=i;@(posedge clk);#1;
   if(data!==stream[p+i])$fatal(1,"head data");end
  for(i=0;i<12;i=i+1)begin @(negedge clk);wr=1;idx=i;
   case(i)
   0:ack=stream[p]==3;1:ack=stream[p];10:ack=8'h65;11:ack=8'h9a;
   default:ack=stream[p+i];endcase
   @(posedge clk);end
  @(negedge clk);wr=0;pub=1;@(posedge clk);@(negedge clk);pub=0;
  repeat(25)@(posedge clk);#1;retired=retired+1;
  if(fault||dut.retired!=retired)$fatal(1,"checked retirement");
 end endtask
 initial begin
  $readmemh("stream.hex",stream);#80;reset=0;
  while(retired<@COUNT@)begin
   while(accepted<@COUNT@ && accepted-retired<4)send_head();
   consume_head();
  end
  if(ready || partials!=@PARTIAL@)$fatal(1,"final counters");
  position=0;corrupt=1;send_head();if(!fault || ready)$fatal(1,"bad CRC accepted");
  reset=1;#80;reset=0;#80;if(ready||fault||dut.retired||dut.accepted)$fatal(1,"STOP");
  $display("PASS trim514 E1 ordinary=%0d partial=%0d",retired,partials);$finish;
 end
endmodule"""
def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(a.rtl,a.out/'nes_sink_spi165.sv')
    stream=bytearray()
    count=partials=0
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _,_,body,_=json.loads(line)
        b=bytes.fromhex(body)
        if b[0]==7:continue
        count+=1;partials+=b[0]==10
        stream+=len(b).to_bytes(2,'little')+b+binascii.crc_hqx(b'\xe1'+b,65535).to_bytes(2,'big')
    assert partials and count>partials
    (a.out/'stream.hex').write_text('\n'.join(f'{v:02x}' for v in stream)+'\n')
    (a.out/'tb.sv').write_text(TB.replace('@LAST@',str(len(stream)-1)).replace('@COUNT@',str(count)).replace('@PARTIAL@',str(partials)))
    (a.out/'pins.json').write_text(json.dumps(dict(ordinary=count,partial=partials,RTL_SHA256=sha(a.rtl),trace_SHA256=sha(a.trace/'packets.jsonl'))))
def run(a):
    for tool,args in [('vlib',['work']),('vlog',['-sv','nes_sink_spi165.sv','tb.sv']),
                      ('vsim',['-c','-quiet','-do','onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0','trim514_queue_tb'])]:
        with (a.out/f'{tool}.log').open('wb') as log:
            subprocess.run([str(a.bin/f'{tool}.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
    assert 'PASS trim514 E1' in (a.out/'vsim.log').read_text()
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,**json.loads((a.out/'pins.json').read_text())),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare','run'))
    for name in ('out','rtl','trace','bin'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();(prepare if a.mode=='prepare' else run)(a)
