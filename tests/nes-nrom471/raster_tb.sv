// SPDX-License-Identifier: MIT
module raster471_tb;
 nes_native_export203 dut(.clk(1'b0),.reset(1'b1),.enable(1'b0),.frame_owned(1'b0),.geometry_valid(1'b0),.frame_generation(16'd0),.patch_count(3'd0),.row_count(8'd0),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd0),.palette_count(6'd0),.response(1'b0),.hit(1'b0),.data(64'd0),.tx_ready(1'b0),.ack_valid(1'b0),.ack_accept(1'b0),.ack_generation(16'd0));
 initial begin
  #1;
  if(dut.next_y(15'h0000)!==15'h1000)$fatal(1,"fine0");
  if(dut.next_y(15'h6000)!==15'h7000)$fatal(1,"fine6");
  if(dut.next_y(15'h7000)!==15'h0020)$fatal(1,"coarse0");
  if(dut.next_y(15'h73a0)!==15'h0800)$fatal(1,"row29");
  if(dut.next_y(15'h73e0)!==15'h0000)$fatal(1,"row31");
  if(dut.next_y(15'h7fbf)!==15'h041f)$fatal(1,"nt29");
  if(dut.next_y(15'h7fff)!==15'h0c1f)$fatal(1,"nt31");
  $display("PASS471 RTL raster wrap cases=7");$finish;
 end
endmodule
