// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Focused raw-phase cancellation/backpressure. Fill completion is a stub;
// the separate wire test uses the actual fill and SPI implementations.
module wire181_faults_tb;
 reg clk=0,reset=1,enable=0,owned=0,response=0,hit=1,fb=0,fd=0;
 reg [63:0] data=0;reg ready=0,av=0;wire release_frame,q,fs,valid,ar,busy;
 wire [2:0] kind;wire [12:0] index;wire [15:0] gen;wire [95:0] tx;wire [3:0] error,state;
 integer mode=0,ticks=0,raw=0,commits=0,aborts=0,tests=0;
 reg phase=0,stalled=0;reg [95:0] held;
 always #5 clk=~clk;
 nes_native_export181 #(.MAX_CYCLES(12000)) dut(
  .clk(clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(16'd12),.patch_count(3'd1),
  .row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),.release_frame(release_frame),
  .query(q),.query_kind(kind),.query_index(index),.query_generation(gen),.response(response),.hit(hit),.data(data),
  .fill_start(fs),.fill_busy(fb),.fill_done(fd),.fill_success(1'b1),.fill_error(4'd0),
  .byte_valid(1'b0),.byte_ready(),.byte_data(8'd0),.byte_tile(13'd0),.byte_lane(4'd0),.byte_kind(2'd0),.byte_generation(16'd12),
  .tx_valid(valid),.tx_ready(ready),.tx_data(tx),.ack_valid(av),.ack_accept(1'b1),.ack_generation(16'd12),.ack_ready(ar),.busy(busy),.error(error),.observe_state177(state));
 always @(negedge clk)begin
  if(!reset)begin
   ready=mode==5&&phase?0:(ticks%7<3);
   // ABORT must still be able to drain after the stall-induced deadline.
   if(state==10)ready=1;
  end
 end
 always @(posedge clk)begin
  response<=q;hit<=!(mode==1&&kind==7);data<=mode==2&&kind==7?64'd64:{58'd0,index[5:0]};
  if(reset)begin fb<=0;fd<=0;av<=0;end
  else begin
   ticks<=ticks+1;
   if(fs)fb<=1;
   if(fb)begin fb<=0;fd<=1;end
   if(release_frame)owned<=0;
   if(q&&kind==7)begin phase<=1;if(mode==3)owned<=0;if(mode==4)enable<=0;end
   if(stalled&&valid&&tx!=held)$fatal(1,"unstable stalled record");
   stalled<=valid&&!ready;held<=tx;
   if(valid&&ready)begin
    if(tx[95:93]==6)begin
     if(!phase||tx[76:64]!=raw||tx[63:0]!=(raw&63))$fatal(1,"raw order/data");raw<=raw+1;
    end
    if(tx[95:93]==7&&tx[76:64]==1)av<=1;
    if(tx[95:93]==7&&tx[76:64]==3)commits<=commits+1;
    if(tx[95:93]==7&&tx[76:64]==2)aborts<=aborts+1;
   end
  end
 end
 initial begin
  for(mode=0;mode<7;mode=mode+1)begin
   @(negedge clk);reset=1;enable=0;owned=0;repeat(4)@(negedge clk);
   ticks=0;raw=0;commits=0;aborts=0;phase=0;stalled=0;
   reset=0;enable=1;owned=1;
   if(mode==6)begin
    wait(phase&&valid&&!ready);@(negedge clk);reset=1;enable=0;owned=0;
    repeat(4)@(negedge clk);if(valid||busy||commits||aborts)$fatal(1,"reset leaked tentative frame");
   end else begin
    wait(commits||aborts);repeat(4)@(negedge clk);
    if(mode==0)begin if(commits!=1||aborts||raw!=256||error)$fatal(1,"normal failed");end
    else if(commits||aborts!=1||error!=(mode<3?3:1))$fatal(1,"bad failure mode=%0d error=%0d",mode,error);
   end
   tests=tests+1;
  end
  $display("PASS WIRE181FAULT cases=%0d",tests);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
