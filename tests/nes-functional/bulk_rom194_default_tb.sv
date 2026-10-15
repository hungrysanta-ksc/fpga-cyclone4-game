// SPDX-License-Identifier: MIT
// Differential default4096 decode against immutable deployed source.
`timescale 1ns/1ps
module bulk_rom194_default_tb;
 reg clk=0;always #5.952 clk=~clk;
 reg reset=1;reg [23:0] a=0;reg rd=1,wr=1,rs=1;
 wire [7:0] d0,d1;wire o0,o1,r0,r1;
 nes_sink_bus165 current_bus(.clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.fault(1'b0),
 .address(a),.read_n(rd),.write_n(wr),.romsel_n(rs),.data_in(8'd0),.data_out(d0),.oe_n(o0),.dir(r0),
 .packet_ready(1'b1),.packet_length(9'd16),.packet_data(8'h39),.packet_address(),.ack_write(),.ack_index(),.ack_byte(),.ack_publish(),.pad_commit(),.pad_buttons());
 nes_sink_bus165_reference original_bus(.clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.fault(1'b0),
 .address(a),.read_n(rd),.write_n(wr),.romsel_n(rs),.data_in(8'd0),.data_out(d1),.oe_n(o1),.dir(r1),
 .packet_ready(1'b1),.packet_length(9'd16),.packet_data(8'h39),.packet_address(),.ack_write(),.ack_index(),.ack_byte(),.ack_publish(),.pad_commit(),.pad_buttons());
 integer i;
 initial begin
  repeat(6)@(negedge clk);reset=0;
  for(i=0;i<32768;i=i+1)begin
   @(negedge clk);a=24'h008000+i;rd=0;rs=0;repeat(6)@(negedge clk);
   if({d0,o0,r0}!=={d1,o1,r1})$fatal(1,"default ROM changed %h",a);
  end
  for(i=0;i<256;i=i+1)begin
   @(negedge clk);a=24'h400000+i;rs=1;repeat(6)@(negedge clk);
   if({d0,o0,r0}!=={d1,o1,r1})$fatal(1,"packet mapping changed %h",a);
  end
  $display("PASS DEFAULT194 reads=33024");$finish;
 end
endmodule
