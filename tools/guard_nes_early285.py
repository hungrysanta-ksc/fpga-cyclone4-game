# SPDX-License-Identifier: MIT
"""Probe the unchanged284 plan lease gate, STOP and immutable bank ownership."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import sha
from probe_nes_joint266 import run

TB=r'''
`timescale 1ns/1ps
module early285_tb;
 reg h=0,n=0,reset=1,stop=0,lease=0,wv=0,seal=0;
 always #5 h=!h;always #22.727 n=!n;
 reg [7:0] wd=0;reg [15:0] gen=1,crc=0;
 wire wr,idle,fault,pv,ev;wire [1:0] kind;integer checks=0;
 nes_plan_batch206 dut(.host_clk(h),.nes_clk(n),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.retire(1'b0),.retire_done(),.retire_permitted(1'b0),.retire_commit(),
 .seal(seal),.seal_length(10'd3),.seal_plans(5'd1),.seal_crc(crc),.host_idle(idle),.fault(fault),
 .lease_valid(lease),.lease_generation(gen),.plan_valid(pv),.plan_ready(1'b0),.tile_done(1'b0),
 .plan_kind(kind),.plan_generation(),.plan_slot(),.plan_tag(),.plan_rows(),.plan_mask(),.plan_alt_mask(),.plan_alt_tags(),
 .end_valid(ev),.end_ready(1'b0),.end_generation());
 function automatic [15:0] c16(input [15:0] p,input [7:0] b);
 reg [15:0] c;begin c=p^{b,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end endfunction
 task clear(input reg owned);begin
 reset=1;stop=0;seal=0;wv=0;lease=owned;gen=1;repeat(10)@(negedge n);reset=0;repeat(10)@(negedge n);
 if(!idle||fault||pv||ev)$fatal(1,"reset");end endtask
 task byteput(input [7:0] b);begin
 @(negedge h);if(!wr)$fatal(1,"no write credit");wd=b;wv=1;@(negedge h);wv=0;end endtask
 task packet(input reg corrupt);begin
 byteput(8'h82);byteput(1);byteput(0);crc=c16(c16(c16(16'hffff,8'h82),1),0)^corrupt;
 @(negedge h);seal=1;@(negedge h);seal=0;
 end endtask
 task quiet;begin repeat(40)@(negedge n);if(pv||ev)$fatal(1,"uncommitted work escaped");end endtask
 initial begin
 clear(0);packet(0);wait(fault);quiet();checks++; // Early seal faults, no safe prefetch today.
 clear(1);packet(0);wait(pv);if(fault||kind!=2)$fatal(1,"valid plan");checks++;
 // The single first plan has already been decoded into held fields, so its
 // RAM bank is free. Two further packets may occupy the two RAM banks.
 packet(0);repeat(12)@(negedge n);if(!idle||fault||!pv)$fatal(1,"decoded bank not released");
 packet(0);repeat(12)@(negedge n);if(idle||wr||fault||!pv)$fatal(1,"two pending bank ownership");checks++;
 stop=1;#1;if(pv||ev||wr)$fatal(1,"STOP exposed plan");quiet();checks++;
 clear(1);packet(1);wait(fault);quiet();checks++;
 clear(1);gen=2;packet(0);wait(fault);quiet();checks++;
 clear(1);byteput(8'h82);stop=1;quiet();if(wr)$fatal(1,"partial write after STOP");checks++;
 clear(1);packet(0);wait(pv);lease=0;wait(fault);quiet();checks++;
 $display("PASS EARLY285 checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"early285 timeout");end
endmodule
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    names=['nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
    for n in names:shutil.copyfile(a.source/n,d/n)
    (d/'early285_tb.sv').write_text(TB,encoding='utf-8',newline='\n')
    shutil.copyfile(__file__,d/Path(__file__).name)
    run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
    run(a.questa_bin/'vlog.exe',['-sv',*names,'early285_tb.sv'],d,'vlog')
    log=run(a.questa_bin/'vsim.exe',['-c','work.early285_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
    assert 'PASS EARLY285 checks=8' in log
    (d/'result.json').write_text(json.dumps(dict(passed=True,checks=8,RTL_unchanged=True,rtl_hashes={n:sha(d/n) for n in names},TB_sha256=sha(d/'early285_tb.sv'),script_sha256=sha(Path(__file__))),indent=2)+'\n')
    print('PASS EARLY285 checks=8')


if __name__=='__main__':main()
