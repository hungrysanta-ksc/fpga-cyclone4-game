// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Actual exporter, modeled consumer: same total budget as installed165.
module native_wait166_tb;
 parameter integer GAP=100;
 reg clk=0,reset=1;always #23.280423 clk=~clk;
 reg frame_owned=1;wire release_frame,query,fill_start,byte_ready,tx_valid,ack_ready,busy;
 wire [2:0] query_kind;wire [12:0] query_index;wire [15:0] query_generation;
 wire [95:0] tx_data;wire [3:0] error;
 reg response=0,fill_busy=0,fill_done=0,ack_valid=0;
 integer ticks=0,records=0,commits=0,aborts=0;
 wire tx_ready=ticks%GAP==0;
 nes_native_export165 #(.MAX_CYCLES(4194304)) dut(
 .clk(clk),.reset(reset),.enable(1'b1),.frame_owned(frame_owned),.geometry_valid(1'b1),.frame_generation(16'd12),
 .row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),
 .release_frame(release_frame),.query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),
 .response(response),.hit(1'b1),.data(64'd0),.fill_start(fill_start),.fill_busy(fill_busy),.fill_done(fill_done),.fill_success(1'b1),
 .byte_valid(1'b0),.byte_ready(byte_ready),.byte_data(8'd0),.byte_tile(13'd0),.byte_lane(4'd0),.byte_kind(2'd0),.byte_generation(16'd12),
 .tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),.ack_valid(ack_valid),.ack_accept(1'b1),.ack_generation(16'd12),.ack_ready(ack_ready),.busy(busy),.error(error));
 always @(posedge clk)begin
  ticks<=ticks+1;response<=query;ack_valid<=0;
  if(fill_start)fill_busy<=1;
  else if(fill_busy)begin fill_busy<=0;fill_done<=1;end
  if(release_frame)frame_owned<=0;
  if(!reset&&tx_valid&&tx_ready)begin
   records<=records+1;
   if(tx_data[95:93]==7)case(tx_data[76:64])
    1:ack_valid<=1;
    2:begin if(tx_data[3:0]!=1)$fatal(1,"wrong abort");aborts<=aborts+1;end
    3:commits<=commits+1;
   endcase
  end
 end
 initial begin
  repeat(4)@(negedge clk);reset=0;
  wait(commits+aborts!=0);@(negedge clk);
  if(GAP==100)begin if(commits!=1||aborts!=0||error!=0)$fatal(1,"fast control");end
  else if(commits!=0||aborts!=1||error!=1||fill_done)$fatal(1,"paced geometry timeout");
  $display("PASS WAIT166 gap=%0d records=%0d commits=%0d aborts=%0d cycles=%0d",GAP,records,commits,aborts,ticks);$finish;
 end
 initial begin #300000000;$fatal(1,"watchdog");end
endmodule
