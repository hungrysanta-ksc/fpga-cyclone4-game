// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_history175_tb;
 reg clk=0,reset=1,active=0,freeze=0,sample_valid175=0;
 reg [95:0] sample=0;reg [7:0] command=0;wire [55:0] page;
 always #5 clk=~clk;
 nes_ppu_history157 dut(.*);
 integer checks=0,i;
 task check(input bit pass,input string why);
  begin checks++;if(!pass)$fatal(1,"%s page=%h",why,page);end
 endtask
 task read_page(input [7:0] cmd,input [55:0] expected);
  begin command=cmd;repeat(2)@(negedge clk);check(page===expected,"page mismatch");end
 endtask
 task send(input integer value);
  begin sample={8'ha4,56'd0,32'(value)};sample_valid175=1;@(negedge clk);sample_valid175=0;
   sample=96'hbad;repeat(7)@(negedge clk);end
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;active=1;
  repeat(20)@(negedge clk);read_page(8'h77,{8'he5,8'd0,8'd0,8'd0,8'd2,8'd96,8'd1});
  for(i=1;i<=20;i++)send(i);
  active=0;repeat(2)@(negedge clk);
  read_page(8'h77,{8'he5,8'd1,8'd16,8'd4,8'd2,8'd96,8'd1});
  for(i=5;i<=20;i++)begin
   read_page(8'ha0|(((i-1)&15)<<1),{8'he5,8'ha4,40'd0});
   read_page(8'ha1|(((i-1)&15)<<1),{8'he5,16'd0,32'(i)});
  end
  active=1;send(99);read_page(8'ha1|6,{8'he5,16'd0,32'd20});
  reset=1;@(negedge clk);reset=0;active=1;
  send(1);sample={8'ha4,56'd0,32'd2};freeze=1;@(negedge clk);freeze=0;sample=96'hbad;
  repeat(3)@(negedge clk);read_page(8'h77,{8'he5,8'd3,8'd2,8'd2,8'd2,8'd96,8'd1});
  read_page(8'ha3,{8'he5,16'd0,32'd2});
  read_page(8'ha4,56'd0);
  $display("PASS HISTORY175 checks=%0d sparse20 retained16 fault_included=1 stop_retained=1",checks);$finish;
 end
endmodule
