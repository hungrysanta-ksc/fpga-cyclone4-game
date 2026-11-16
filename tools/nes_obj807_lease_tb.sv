`timescale 1ns/1ps
module nes_obj807_lease_tb;
 reg clk=0, stop=1, start=0, owned=0, decision=0, accept=0, retire=0, ready=1;
 reg [15:0] generation=0;
 wire release_frame, exported, permitted, lease, can_retire, fault;
 wire query,ack_ready,valid;
 wire [95:0] record_data;
 wire [3:0] error_code,state_id;
 wire [15:0] held;
 always #5 clk=~clk;
 nes_native_export203 source(.clk(clk),.reset(stop),.enable(1'b1),
   .start_permitted(1'b1),.discard_permitted(permitted),.frame_owned(owned),
   .geometry_valid(1'b1),.frame_generation(generation),.patch_count(3'd0),
   .row_count(8'd224),.object_count(8'd33),.exception_count(8'd0),
   .group_count(6'd1),.palette_count(6'd1),.release_frame(exported),
   .query(query),.response(1'b1),.hit(1'b1),.data(64'd0),
   .tx_valid(valid),.tx_ready(ready),.tx_data(record_data),.ack_valid(decision),
   .ack_accept(accept && permitted),.ack_generation(generation),.ack_ready(ack_ready),
   .observe_state177(state_id),.error(error_code));
 nes_capture_lease201 owner(.clk(clk),.reset(stop),.stop(stop),.capture_begin(start),
   .frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
   .export_release(exported),.export_error(error_code),.source_ready(1'b1),
   .source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd1),.reader_drained(1'b1),
   .retire_commit(retire),.retire_generation(generation),.release_frame(release_frame),
   .lease_valid(lease),.retire_permitted(can_retire),.export_permitted(permitted),
   .captured_generation(held),.fault(fault));
 task tick;
   @(negedge clk);
   if(fault) $fatal(1,"unexpected lease fault");
 endtask
 task frame(input bit admit,input bit stop_pending);
   start=1;tick();start=0;generation++;owned=1;
   while(state_id!=8) tick();
   accept=admit;decision=1;tick();decision=0;
   if(!valid || record_data[92:77]!=generation || record_data[76:64]!=(admit?3:2)
      || record_data[63:0]!=(admit?0:6)) $fatal(1,"incorrect terminal record");
   ready=0;
   if(!admit)begin
     tick();owned=0;
     repeat(3)begin tick();if(lease||!valid) $fatal(1,"rejected lease");end
   end
   if(stop_pending)begin
     stop=1;tick();if(valid||lease||can_retire) $fatal(1,"STOP publication");
     stop=0;
   end else begin
     ready=1;tick();
     if(admit)begin
       tick();owned=0;
       if(!lease||!can_retire||held!=generation) $fatal(1,"accepted lease");
       retire=1;tick();retire=0;
     end
   end
   ready=1;tick();tick();
   if(lease||!permitted) $fatal(1,"next capture blocked");
 endtask
 initial begin
   tick();stop=0;frame(1,0);frame(0,0);frame(0,0);frame(1,0);
   frame(0,1);frame(1,0);$display("OBJ807_EXPORT_LEASE_PASS");$finish;
 end
 initial begin #2000000;$fatal(1,"export timeout");end
endmodule
