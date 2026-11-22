`timescale 1ns/1ps
module tb_nes_first918;
 reg n=0,h=0,reset=1,stop=0,valid=0,consume=0,e=0;
 reg [31:0] expected_token=9;
 reg [4:0] idx=0;
 always #20 n=~n;
 always #6 h=~h;
 wire ready,chunk,ended,fault,er;
 wire [11:0] size;
 wire [31:0] token;
 wire [15:0] generation;
 nes_tile_bulk206 dut(.nes_clk(n),.host_clk(h),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
  .plan_valid(1'b0),.plan_taken(1'b0),.plan_kind(2'd2),.plan_slot(10'd0),.plan_generation(16'd7),
  .tile_valid(valid),.tile_ready(ready),.tile_data(8'd0),.tile_index(idx),.tile_length(6'd16),
  .tile_kind(2'd2),.tile_slot(10'd0),.tile_generation(16'd7),.end_valid(e),.end_ready(er),.end_generation(16'd7),
  .token_seed(32'd9),.chunk_ready(chunk),.chunk_length(size),.chunk_token(token),.chunk_generation(generation),
  .consume(consume),.consume_token(expected_token),.address(24'd0),.read_n(1'b1),.write_n(1'b1),.fault(fault),.end_sealed(ended));
 task automatic send_bytes(input integer count);
  for(integer i=0;i<count;i++)begin
   @(negedge n);while(!ready)@(negedge n);
   idx=i;valid=1;@(negedge n);valid=0;
  end
 endtask
 task automatic cancel;
  stop=1; repeat(4)@(negedge n);
  if(chunk||ended||fault)$fatal(1,"STOP ownership");
  stop=0;repeat(8)@(negedge n);
  if(chunk||ended||fault)$fatal(1,"stale result");
 endtask
 initial begin
  repeat(4)@(negedge n);reset=0;
  send_bytes(15);repeat(42)@(negedge h);if(chunk||ended)$fatal(1,"partial tile");cancel();
  send_bytes(16);wait(dut.state==dut.SEAL);@(negedge h);if(chunk||ended)$fatal(1,"early publish");cancel();
  send_bytes(16);wait(chunk);@(negedge h);
  if(token!=9||size!=16||generation!=7||ended||fault)$fatal(1,"descriptor");
  cancel();send_bytes(16);wait(chunk);@(negedge h);
  consume=1;@(negedge h);consume=0;if(chunk||ended)$fatal(1,"consume");
  @(negedge n);while(!er)@(negedge n);e=1;@(negedge n);e=0;
  wait(ended);if(fault||chunk)$fatal(1,"END");
  $display("PASS918 partial/preseal/published STOP, restart, checked consume and END");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
