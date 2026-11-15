// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Isolate the last COMMIT of generation 953. The preceding data records go
// to a ready sink; D3, both CDC mailboxes, COMMIT, D0/D1/D2 use board RTL.
module commit790_tb;
 reg nc=0,hc=0,reset=1;
 always #23.280423 nc=~nc;
 always #5.952381 hc=~hc;
 `include "spi200_bus.svh"
 wire [3:0] state,err;
 wire rel,valid,src_ready,host_valid,host_ready,ack_valid,ack_ready,accept,prepared,consumed;
 wire [95:0] word_in,word_out;
 wire [15:0] generation;
 wire [16:0] ack_msg;
 wire fault;
 wire terminal=word_in[95:93]==7 && word_in[76:64]==3;
 nes_native_export203 producer(.clk(nc),.reset(reset),.enable(1'b1),.start_permitted(1'b1),
  .discard_permitted(1'b1),.frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(16'd953),
  .patch_count(3'd0),.row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),
  .group_count(6'd1),.palette_count(6'd1),.release_frame(rel),.response(1'b1),.hit(1'b1),.data(64'd0),
  .tx_valid(valid),.tx_ready(!terminal||src_ready),.tx_data(word_in),.ack_valid(prepared),
  .ack_ready(consumed),.ack_accept(ack_msg[16]),.ack_generation(ack_msg[15:0]),.observe_state177(state),.error(err));
 nes_native_mailbox165 #(.WIDTH(17)) request_box(.src_clk(hc),.dst_clk(nc),.reset(reset),
  .src_valid(ack_valid),.src_ready(ack_ready),.src_data({accept,generation}),
  .dst_valid(prepared),.dst_ready(consumed),.dst_data(ack_msg));
 nes_native_mailbox165 #(.WIDTH(96)) record_box(.src_clk(nc),.dst_clk(hc),.reset(reset),
  .src_valid(valid&&terminal),.src_ready(src_ready),.src_data(word_in),
  .dst_valid(host_valid),.dst_ready(host_ready),.dst_data(word_out));
 nes_native_spi165 spi(.clk(hc),.reset(reset),.SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),
  .selected(selected197),.miso(miso197),.record_valid(host_valid),.record_ready(host_ready),.record_data(word_out),
  .ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(accept),.ack_generation(generation),.fault(fault));
 realtime d3_end,release_time,ready_time;
 always @(posedge rel) if(!reset)release_time=$realtime;
 always @(posedge spi.available) if(!reset)ready_time=$realtime;
 task command(input [7:0] op,input [15:0] id,input [7:0] arg);
  reg [7:0] b[0:7];integer k;
  begin
   b[0]=op;b[1]=0;b[2]=id[15:8];b[3]=id[7:0];b[4]=arg;b[5]=~arg;b[6]=0;b[7]=8'ha5;
   for(k=0;k<6;k=k+1)b[6]=crc8_197(b[6],b[k]);
   begin197();for(k=0;k<8;k=k+1)byte197(b[k],rx197[k]);
   if(op==8'hd3)d3_end=$realtime+SPI_HOLD;
   end197();
  end
 endtask
 integer k;reg [7:0] crc8;reg [15:0] crc16;integer bitno;
 initial begin
  #1000;@(negedge nc);reset=0;wait(state==8);
  command(8'hd3,953,1);command(8'hd0,0,0);
  crc8=0;for(k=1;k<7;k=k+1)crc8=crc8_197(crc8,rx197[k]);
  if(!rx197[2][0]||{rx197[3],rx197[4],rx197[5],rx197[6]}!=32'd12||rx197[1]!=8'hd6||rx197[7]!=crc8)$fatal(1,"invalid COMMIT status");
  if(!(d3_end<release_time && release_time<ready_time && ready_time<$realtime))$fatal(1,"mailbox release order");
  begin197();byte197(8'hd1,rx197[0]);for(k=1;k<15;k=k+1)byte197(0,rx197[k]);end197();
  if({rx197[1],rx197[2],rx197[3],rx197[4]}!={16'he003,16'd953})$fatal(1,"COMMIT identity");
  crc16=16'hffff;
  for(k=1;k<=12;k=k+1)begin
   if(k>4 && rx197[k]!=0)$fatal(1,"COMMIT payload");
   crc16=crc16^{rx197[k],8'd0};
   for(bitno=0;bitno<8;bitno=bitno+1)crc16=crc16[15]?(crc16<<1)^16'h1021:crc16<<1;
  end
  if({rx197[13],rx197[14]}!=crc16)$fatal(1,"COMMIT CRC");
  command(8'hd2,0,0);command(8'hd0,0,0);
  crc8=0;for(k=1;k<7;k=k+1)crc8=crc8_197(crc8,rx197[k]);
  if(fault||err||rx197[2][0]||{rx197[3],rx197[4]}!=1||rx197[7]!=crc8)$fatal(1,"retirement");
  $display("PASS COMMIT790 D3_to_release_ns=%.3f D3_to_available_ns=%.3f",release_time-d3_end,ready_time-d3_end);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
