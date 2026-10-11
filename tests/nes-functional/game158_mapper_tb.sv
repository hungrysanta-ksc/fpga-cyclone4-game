// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module mapper158_tb;
 reg clk=0,reset=1,ce=0,preview=0,write=0;
 always #23.280423 clk=~clk;
 reg [15:0] a=0;reg [7:0] d=0;reg [13:0] p=14'h218;
 wire [21:0] actual,hint;
 cart_top dut(.clk(clk),.reset(reset),.ce(ce),.cpu_ce(1'b0),.paused(1'b0),
 .game158_preview_write(preview),.game148_hint_logic(p),.game148_hint_physical(hint),
 .prg_ain(a),.prg_din(d),.prg_write(write),.prg_read(1'b0),.prg_mask(21'h3ffff),
 .chr_ain_orig(p),.chr_ain_ex(p),.chr_ex(1'b0),.chr_mask(20'h1ffff),
 .chr_read(1'b0),.chr_write(1'b0),.chr_din(8'd0),.chr_aout(actual),.audio_in(16'd0));
 task wr(input [15:0] addr,input [7:0] data);
  @(negedge clk);a=addr;d=data;write=1;ce=1;preview=1;
  @(negedge clk);ce=0;write=0;preview=0;#1;
 endtask
 reg [21:0] prior,next_address;
 integer inv,sel,value,page,checks=0;
 task compare_commit(input [15:0] addr,input [7:0] data);
  @(negedge clk);prior=actual;a=addr;d=data;preview=1;write=0;ce=0;#1;next_address=hint;
  repeat(3)begin @(posedge clk);#1;if(actual!==prior)$fatal(1,"normal mapper changed before CE");end
  // Cancel speculation: no state was committed.
  @(negedge clk);preview=0;#1;if(hint!==actual)$fatal(1,"cancelled hint changed state");
  preview=1;#1;if(hint!==next_address)$fatal(1,"unstable pure lookup");
  write=1;ce=1;@(negedge clk);ce=0;write=0;preview=0;#1;
  if(actual!==next_address || hint!==actual)$fatal(1,"prediction != committed mapping a=%h d=%h p=%h prior=%h expected=%h actual=%h",addr,data,p,prior,next_address,actual);
  checks++;
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;
  for(inv=0;inv<2;inv++)for(sel=0;sel<8;sel++)for(value=0;value<4;value++)for(page=0;page<8;page++)begin
   p=(page<<10)|14'h218;
   wr(16'h8000,(inv<<7)|sel);wr(16'h8001,8'h16);
   compare_commit(16'h8001,value==0?8'h00:value==1?8'h17:value==2?8'h5e:8'hff);
  end
  for(inv=0;inv<2;inv++)for(page=0;page<8;page++)begin
   p=(page<<10)|14'h218;wr(16'h8000,(inv<<7)|1);
   compare_commit(16'h8000,((1-inv)<<7)|1);
  end
  for(page=0;page<8;page++)begin
   p=(page<<10)|14'h218;compare_commit(16'ha000,8'h01);
  end
  if(checks!=536)$fatal(1,"case count");
  $display("PASS158 mapper lookup %0d commits, no early state and cancelled speculation",checks);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
