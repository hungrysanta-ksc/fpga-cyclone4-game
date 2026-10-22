# SPDX-License-Identifier: MIT
"""Real SPI pins: shared CRC domains, publication, credit and STOP."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha

TB=r'''
`timescale 1ns/1ps
module test;
 reg clk=0,nclk=0;always #5 clk=~clk;always #22.727 nclk=~nclk;
 reg reset=1,stop=0,ss=1,sck=0,mosi=0;wire [109:0] link;
 wire [183:0] qs,ps;wire pc,qc,irq,mode;
 wire qfault,pfault,bfault,qr;wire [8:0] qlen;wire [7:0] qdata;
 wire pw,pr,seal,idle,retire,rd,ev,partial,pv;
 wire [7:0] pd;wire [9:0] len;wire [4:0] plans;wire [15:0] crc;
 integer seals=0,commits=0;reg parser_retire=0;
 reg evq=0;always @(posedge clk)if(reset||stop)evq<=0;else evq<=ev;
 nes_spi270 spi(.clk(clk),.reset(reset||stop),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
 .source_status(184'd0),.output_status(qs),.plan_status(ps),.progress_irq284(irq),.progress_mode284(mode),.request_crc_enable(pc),.link(link));
 nes_queue260 queue(.link270(link),.status270(qs),.crc_take270(qc),.progress_status(128'd0),.parser_retire(parser_retire),
 .clk(clk),.reset(reset||stop),.enable(1'b1),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(),.miso(),
 .sn_address(8'd0),.sn_data(qdata),.packet_ready(qr),.packet_length(qlen),.fault(qfault));
 nes_plan_spi200 ep(.link270(link),.status270(ps),.crc_take270(pc),.clk(clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(bfault),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(),.miso(),.fault(pfault),.plan_idle(idle),.plan_ready(pr),
 .plan_write(pw),.plan_data(pd),.plan_seal(seal),.plan_length(len),.plan_plans(plans),.plan_crc(crc),.retire_done(rd),.retire(retire),
 .end_generation(16'd1),.chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),.end_sealed(ev&&!evq&&!partial));
 nes_plan_batch206 #(.SHARED_CRC307(1)) batch(.host_clk(clk),.nes_clk(nclk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(pfault),
 .write_valid(pw),.write_ready(pr),.write_data(pd),.retire(retire),.retire_done(rd),.retire_permitted(1'b1),.retire_commit(),
 .seal(seal),.seal_length(len),.seal_plans(plans),.seal_crc(crc),.host_idle(idle),.fault(bfault),.lease_valid(1'b1),.lease_generation(16'd1),
 .plan_valid(pv),.plan_ready(1'b0),.tile_done(1'b0),.plan_kind(),.plan_generation(),.plan_slot(),.plan_tag(),.plan_rows(),.plan_mask(),.plan_alt_mask(),.plan_alt_tags(),
 .end_valid(ev),.end_partial295(partial),.end_ready(1'b1),.end_generation());
 always @(posedge clk)begin
  if(seal)seals++;
  if(stop&&(seal||pr))$fatal(1,"STOP publish/write gate");
 end
 always @(posedge nclk)if(ev)commits++;
 reg [7:0] tx[0:300];integer n;
 function automatic [7:0] c8(input [7:0] c0,b);reg [7:0] c;begin c=c0^b;for(integer j=0;j<8;j++)c=c[7]?(c<<1)^8'h07:c<<1;return c;end endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);reg [15:0] c;begin c=c0^{b,8'd0};for(integer j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction
 task fresh;begin ss=1;sck=0;stop=0;reset=1;#500;reset=0;#1000;seals=0;commits=0;end endtask
 task e9(input integer bad);reg [15:0] c;reg [7:0] h;begin
 tx[0]='he9;tx[1]=3;tx[2]=0;tx[3]=1;tx[4]='h83;tx[5]=1;tx[6]=0;
 if(bad==4)tx[3]=0;
 c=16'hffff;for(integer j=4;j<7;j++)c=c16(c,tx[j]);
 if(bad==1)c=c^1;tx[7]=c[15:8];tx[8]=c[7:0];
 h=0;for(integer j=0;j<9;j++)h=c8(h,tx[j]);tx[9]=bad==2?h^1:h;tx[10]='ha5;n=bad==3?10:11;
 end endtask
 task e1(input integer bad);reg [15:0] c;begin
 tx[0]='he1;for(integer j=1;j<17;j++)tx[j]=j;
 c=16'hffff;for(integer j=0;j<17;j++)c=c16(c,tx[j]);if(bad)c=c^1;
 tx[17]=c[15:8];tx[18]=c[7:0];n=19;
 end endtask
 task send(input integer abort_byte);begin
 #200;ss=0;#200;
 for(integer i=0;i<n;i++)begin
  for(integer j=7;j>=0;j--)begin mosi=tx[i][j];#200;sck=1;#200;sck=0;end
  if(i==abort_byte)begin stop=1;#200;end
 end
 #200;ss=1;#3000;
 end endtask
 initial begin
 fresh();e9(0);send(-1);if(pfault||bfault||seals!=1||commits!=1)$fatal(1,"valid E9 pf%0d bf%0d seals%0d commits%0d",pfault,bfault,seals,commits);
 e9(0);send(-1);if(!pfault||seals!=1)$fatal(1,"E9 after closed bank");
 for(integer bad=1;bad<=4;bad++)begin fresh();e9(bad);send(-1);if(!pfault||seals||commits)$fatal(1,"bad E9 admitted %0d",bad);end
 fresh();e9(0);send(5);if(seals||commits||qr)$fatal(1,"STOP exposed E9");
 fresh();e1(0);send(-1);if(qfault||!qr||qlen!=16)$fatal(1,"valid E1");
 e9(0);send(-1);if(pfault||bfault||seals!=1||!qr)$fatal(1,"E1/E9 CRC domain reset");
 fresh();e1(1);send(-1);if(!qfault||qr)$fatal(1,"bad E1 admitted");
 fresh();for(integer j=0;j<4;j++)begin e1(0);send(-1);end
 if(qfault||queue.used!=4)$fatal(1,"four credits");
 e1(0);send(-1);if(!qfault||queue.accepted!=4)$fatal(1,"fifth credit accepted");
 fresh();e1(0);send(8);if(qr||queue.accepted)$fatal(1,"STOP exposed E1");
 $display("PASS SPI307 13 boundary checks");$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    names=['nes_spi270.sv','nes_queue260.sv','nes_plan_spi200.sv','nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
    for n in names:shutil.copyfile(a.source/n,d/n)
    (d/'test.sv').write_text(TB,newline='\n');qb=Path('C:/altera_standard/25.1std/questa_fse/win64')
    for cmd,args in [('vlib',['work']),('vlog',['-sv',*names,'test.sv']),('vsim',['-c','test','-do','run -all; quit -f'])]:
        r=subprocess.run([str(qb/(cmd+'.exe')),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
        (d/(cmd+'.log')).write_bytes(r.stdout);assert r.returncode==0 and b'** Error' not in r.stdout and b'** Fatal' not in r.stdout,r.stdout.decode(errors='replace')
    assert 'PASS SPI307' in (d/'vsim.log').read_text()
    result=dict(passed=True,checks=13,script_sha256=sha(Path(__file__)),TB_sha256=sha(d/'test.sv'),rtl_hashes={n:sha(d/n) for n in names})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
