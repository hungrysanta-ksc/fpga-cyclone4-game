// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_chr951;
 reg clk=0, reset=1, invalidate=1, flush=1, demand=0, salt=0;
 always #5 clk=~clk;
 reg [21:0] address=0, returned_address=0;
 reg reply=0;
 wire ready,response,request;
 wire [7:0] lo,hi;
 wire [21:0] physical;
 integer grants=0;
 function automatic [7:0] plane(input [21:0] a,input alt, input image);
  plane=a[16:9]^a[10:3]^{7'b0,alt}^(image?8'hba:8'h3d);
 endfunction
 nes_e9_rows914 #(.COMPACT(1),.CHECK_HINT(1),.SINGLE_READ(1),.COMPLETE_ROW_SET(1)) dut(
   .clk(clk),.reset(reset),.invalidate(invalidate),.flush_rom(flush),
   .hint(1'b0),.tag(13'd0),.mask(8'd0),.demand(demand),.pair(1'b1),.address(address),
   .ready(ready),.response(response),.lo(lo),.hi(hi),.request(request),.physical_address(physical),
   .grant_ready(1'b1),.reply(reply&&!invalidate),.physical_done(reply),.physical_error(1'b0),
   .reply_address(returned_address),.physical_lo(plane(returned_address,0,salt)),.physical_hi(plane(returned_address,1,salt)));
 always @(posedge clk)begin
  reply<=request;
  if(request)begin returned_address<=physical;grants<=grants+1;end
 end
 task automatic read_pair(input [12:0] tag,input integer cost);
  integer prev;
  @(negedge clk);prev=grants;address={5'h10,tag,4'b0010};demand=1;
  do @(posedge clk);while(!ready);
  @(negedge clk);demand=0;
  while(!response)@(negedge clk);
  if(lo!==plane(address,0,salt)||hi!==plane(address,1,salt)||grants!=prev+cost)$fatal(1,"pair tag %d grants %d expected %d: %h/%h != %h/%h",tag,grants-prev,cost,lo,hi,plane(address,0,salt),plane(address,1,salt));
 endtask
 task automatic retire;
  @(negedge clk);invalidate=1;repeat(260)@(negedge clk);invalidate=0;
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;invalidate=0;flush=0;repeat(265)@(negedge clk);
  read_pair(13'h111,1);retire();read_pair(13'h111,0);
  read_pair(13'h151,1);read_pair(13'h111,1);
  @(negedge clk);invalidate=1;flush=1;salt=1;
  repeat(4)@(negedge clk);flush=0;invalidate=0;repeat(265)@(negedge clk);
  read_pair(13'h111,1);read_pair(13'h111,0);
  $display("PASS951 lease reuse, full physical tag, replacement and changed ROM after STOP");$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
