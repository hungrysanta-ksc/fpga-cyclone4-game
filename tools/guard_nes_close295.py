# SPDX-License-Identifier: MIT
"""Actual plan RAM/CDC decoder: nonfinal closure, lease, CRC, STOP and retire."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import sha
from probe_nes_joint266 import run

TB=r'''
`timescale 1ns/1ps
module close295_tb;
 parameter integer CASE=0;
 reg h=0,n=0,reset=1,stop=0,pause_n=0;
 always #5 h=~h;always #23 if(!pause_n)n=~n;
 reg wr=0,seal=0,retire=0,permit=1,er=1;reg [7:0] data=0;
 reg [9:0] length=3;reg [15:0] crc=0;wire ready,idle,fault,pv,ev,ep,rd,commit;
 wire [1:0] kind;reg td=0;wire [15:0] eg;
 integer partials=0,finals=0,tiles=0;
 nes_plan_batch206 dut(.host_clk(h),.nes_clk(n),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(wr),.write_ready(ready),.write_data(data),.retire(retire),.retire_done(rd),.retire_permitted(permit),.retire_commit(commit),
 .seal(seal),.seal_length(length),.seal_plans(5'd1),.seal_crc(crc),.host_idle(idle),.fault(fault),
 .lease_valid(1'b1),.lease_generation(16'd7),.plan_valid(pv),.plan_ready(1'b1),.tile_done(td),.plan_kind(kind),
 .plan_generation(),.plan_slot(),.plan_tag(),.plan_rows(),.plan_mask(),.plan_alt_mask(),.plan_alt_tags(),
 .end_valid(ev),.end_partial295(ep),.end_ready(er),.end_generation(eg));
 always @(posedge n)begin td<=pv;if(pv)tiles<=tiles+1;if(ev&&er)begin
  if(eg!=7)$fatal(1,"wrong generation on completion");
  if(ep)partials<=partials+1;else finals<=finals+1;
 end end
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
 reg [15:0] c;begin c=c0^{b,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction
 task packet(input [7:0] op,input [15:0] gen,input bit corrupt);
 reg [15:0] c;reg [7:0] v;begin
  wait(idle);c=16'hffff;length=op==8'h81 ? 8 : 3;
  for(integer i=0;i<length;i++)begin
   v=i==0?op:i==1?gen[7:0]:i==2?gen[15:8]:i==7?8'hff:0;
   @(negedge h);wait(ready);wr=1;data=v;c=c16(c,v);
  end
  @(negedge h);wr=0;crc=c^(corrupt?16'd1:16'd0);seal=1;
  @(negedge h);seal=0;
 end endtask
 task expected_fault;begin wait(fault);#100;if(pv||ev||ready)$fatal(1,"fault did not gate endpoints");$display("PASS CLOSE295 case=%0d",CASE);$finish;end endtask
 initial begin #100000;$fatal(1,"timeout case %0d",CASE);end
 initial begin
  repeat(5)@(negedge h);reset=0;wait(idle);
  if(CASE==3)begin packet(8'h87,8,0);expected_fault();end
  if(CASE==4)begin packet(8'h87,7,1);expected_fault();end
  if(CASE==5)begin packet(8'h8b,7,0);expected_fault();end
  packet(8'h82,7,0);wait(tiles==1);wait(dut.state==dut.WAIT);
  if(CASE==6||CASE==7)er=0;
  packet(8'h87,7,0);wait(ev);
  if(CASE==6||CASE==7)begin
   if(!ep)$fatal(1,"BG marker became final END");
   if(CASE==7)pause_n=1;
   stop=1;#100;if(pv||ev||ready||commit)$fatal(1,"STOP left activity");
   $display("PASS CLOSE295 case=%0d",CASE);$finish;
  end
  wait(partials==1);wait(dut.state==dut.WAIT);#100;
  if(dut.closed||finals||!dut.bg_closed295)$fatal(1,"partial closes frame");
  if(CASE==1)begin packet(8'h87,7,0);expected_fault();end
  if(CASE==2)begin packet(8'h82,7,0);expected_fault();end
  if(CASE==8)begin @(negedge h);retire=1;@(negedge h);retire=0;expected_fault();end
  packet(8'h81,7,0);wait(tiles==2);wait(dut.state==dut.WAIT);
  packet(8'h83,7,0);wait(finals==1);wait(dut.closed);permit=0;
  @(negedge h);retire=1;@(negedge h);retire=0;
  repeat(20)@(negedge n);if(commit||rd)$fatal(1,"retired without permission");
  permit=1;wait(rd);#100;if(dut.closed||dut.bg_closed295||fault)$fatal(1,"retire did not rearm");
  $display("PASS CLOSE295 case=%0d",CASE);$finish;
 end
endmodule
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--questa-bin',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);names=['nes_domain_reset124.sv','nes_native_mailbox206.sv','nes_plan_batch206.sv'];pins={}
    for name in names:shutil.copyfile(a.source/name,d/name);pins[name]=sha(d/name)
    (d/'close295_tb.sv').write_text(TB,newline='\n');run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
    run(a.questa_bin/'vlog.exe',['-sv',*names,'close295_tb.sv'],d,'vlog')
    for case in range(9):
        log=run(a.questa_bin/'vsim.exe',['-c','work.close295_tb',f'-gCASE={case}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'case{case}',60)
        assert f'PASS CLOSE295 case={case}' in log
    (d/'result.json').write_text(json.dumps(dict(passed=True,cases=list(range(9)),rtl_hashes=pins,tb_sha256=sha(d/'close295_tb.sv'),script_sha256=sha(Path(__file__)),scope=__doc__),indent=2)+'\n')

if __name__=='__main__':main()
