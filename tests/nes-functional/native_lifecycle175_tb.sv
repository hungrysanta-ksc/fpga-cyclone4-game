// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Deployed174 collectors -> fill -> exporter -> two asynchronous mailboxes.
// Synthetic PPU events and memory/host endpoints; no physical SPI or game ROM.
module native_lifecycle175_tb;
 parameter integer DROP_RELEASE=0;
 integer commits=0;
 reg clk=0,host_clk=0,reset=1;
 always #23.280423 clk=~clk;
 initial begin #3.5;forever #5.9523809 host_clk=~host_clk;end
 wire release_frame;
 // Negative control drops the producer release, before host sees COMMIT.
 wire collector_release=release_frame && !DROP_RELEASE;
 reg ppu_ce=0,rom_fault=0;reg [8:0] scanline=0,dot=0;
 reg bg_low=0,bg_high=0;reg [13:0] logical_address=0;reg [21:0] physical_address=0;
 reg [7:0] display_mask=8'h1e;
 wire owned,geometry_valid,initialized,active,response,hit,scroll_seen;
 wire [15:0] generation;wire [24:0] errors;wire [63:0] data;
 wire [7:0] row_count,object_count,exception_count;wire [5:0] group_count,palette_count;
 wire query,fill_query,fill_start,fill_busy,fill_done,fill_success;
 wire [3:0] fill_error,export_error;
 wire [2:0] query_kind,fill_query_kind;wire [12:0] query_index,fill_query_index;
 wire [15:0] query_generation,fill_query_generation;
 nes_native_frame165 frame_dut(.clk(clk),.reset(reset),.release_frame(collector_release),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
  .scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(1'b0),.obj_high(1'b0),.obj_valid(1'b0),.extra_sprites(1'b0),
  .bg_attribute(2'd0),.obj_attribute(8'd0),.obj_x(8'd0),.ppu_read(bg_low||bg_high),.ppu_valid(bg_low||bg_high),
  .logical_address(logical_address),.physical_address(physical_address),.scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),.pattern_mode(3'd0),
  .display_mask(display_mask),.palette(192'd0),.scroll_access(1'b0),
  .query(fill_busy?fill_query:query),.query_kind(fill_busy?fill_query_kind:query_kind),.query_index(fill_busy?fill_query_index:query_index),
  .query_generation(fill_busy?fill_query_generation:query_generation),.owned(owned),.geometry_valid(geometry_valid),.initialized(initialized),.active(active),
  .generation(generation),.errors(errors),.scroll_seen(scroll_seen),.row_count(row_count),.object_count(object_count),.exception_count(exception_count),
  .group_count(group_count),.palette_count(palette_count),.response(response),.hit(hit),.data(data));
 wire mem_request,mem_abort;wire [21:0] mem_address;wire [15:0] mem_generation;
 reg mem_response=0;reg [21:0] mem_reply_address;reg [15:0] mem_reply_generation;reg [7:0] mem_data;
 wire byte_valid,byte_ready;wire [7:0] byte_data;wire [12:0] byte_tile;wire [3:0] byte_lane;wire [1:0] byte_kind;wire [15:0] byte_generation;
 nes_native_fill165 #(.WAIT_CYCLES(131072),.MAX_CYCLES(16777216),.COOPERATIVE_WAIT(1)) fill(
  .clk(clk),.reset(reset),.start(fill_start),.clear(release_frame),.frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .query(fill_query),.query_kind(fill_query_kind),.query_index(fill_query_index),.query_generation(fill_query_generation),.response(response),.hit(hit),.data(data),
  .mem_idle(!mem_response),.mem_ready(!mem_response),.mem_response(mem_response),.mem_error(1'b0),.mem_response_address(mem_reply_address),
  .mem_response_generation(mem_reply_generation),.mem_data(mem_data),.mem_request(mem_request),.mem_abort(mem_abort),.mem_address(mem_address),.mem_generation(mem_generation),
  .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.byte_tile(byte_tile),.byte_lane(byte_lane),.byte_kind(byte_kind),.byte_generation(byte_generation),
  .busy(fill_busy),.done(fill_done),.success(fill_success),.error(fill_error),.quarantine(),.tile_count(),.byte_count(),.cycles());
 always @(posedge clk)begin
  mem_response<=!reset&&mem_request&&!mem_response;
  if(mem_request&&!mem_response)begin mem_reply_address<=mem_address;mem_reply_generation<=mem_generation;mem_data<=mem_address[7:0]^mem_address[15:8];end
 end
 wire tx_valid,tx_ready,ack_valid,ack_ready;wire [95:0] tx_data;wire [16:0] ack_data;
 wire host_valid,host_ready,host_ack_ready;wire [95:0] host_data;reg host_ack_valid=0;reg [16:0] host_ack_data;
 nes_native_export165 #(.MAX_CYCLES(33554432)) exporter(
  .clk(clk),.reset(reset),.enable(1'b1),.frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),
  .release_frame(release_frame),.query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),
  .response(response&&!fill_busy&&!fill_start),.hit(hit&&!fill_busy&&!fill_start),.data(data),.fill_start(fill_start),.fill_busy(fill_busy),.fill_done(fill_done),.fill_success(fill_success),.fill_error(fill_error),
  .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.byte_tile(byte_tile),.byte_lane(byte_lane),.byte_kind(byte_kind),.byte_generation(byte_generation),
  .tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),.ack_valid(ack_valid),.ack_accept(ack_data[16]),.ack_generation(ack_data[15:0]),.ack_ready(ack_ready),.busy(),.error(export_error));
 nes_native_mailbox165 #(.WIDTH(96)) records(.src_clk(clk),.dst_clk(host_clk),.reset(reset),.src_valid(tx_valid),.src_ready(tx_ready),.src_data(tx_data),.dst_valid(host_valid),.dst_ready(host_ready),.dst_data(host_data));
 nes_native_mailbox165 #(.WIDTH(17)) prepared(.src_clk(host_clk),.dst_clk(clk),.reset(reset),.src_valid(host_ack_valid),.src_ready(host_ack_ready),.src_data(host_ack_data),.dst_valid(ack_valid),.dst_ready(ack_ready),.dst_data(ack_data));
 integer begins=0,ends=0,rejects=0,releases=0,held_frames=0,records_seen=0,bytes_seen=0;
 integer host_ticks=0,host_pause=0,ack_delay=0;reg awaiting_ack=0,in_frame=0;
 reg [15:0] receiving_generation=0,last_generation=0;reg stalled=0;reg [95:0] stalled_data;
 // Delays model measured build/seal intervals, not exact MCU/SPI execution.
 // The first pause exceeds ten NES frame periods (170 ms).
 assign host_ready=!reset&&host_pause==0&&host_ticks%1600==0;
 always @(posedge host_clk)begin
  if(!reset)begin
   host_ticks<=host_ticks+1;
   if(host_pause>0)host_pause<=host_pause-1;
   if(stalled&&host_data!==stalled_data)$fatal(1,"held mailbox changed");
   stalled<=host_valid&&!host_ready;stalled_data<=host_data;
   if(host_ack_valid&&host_ack_ready)host_ack_valid<=0;
   if(awaiting_ack)begin
    if(ack_delay>0)ack_delay<=ack_delay-1;
    else begin host_ack_valid<=1;host_ack_data<={1'b1,receiving_generation};awaiting_ack<=0;end
   end
   if(host_valid&&host_ready)begin
    if(host_data[95:93]==7)case(host_data[76:64])
     0:begin
      if(in_frame||host_data[63:48]!=16'h1741||host_data[92:77]<=last_generation)$fatal(1,"invalid BEGIN");
      receiving_generation<=host_data[92:77];in_frame<=1;records_seen<=0;bytes_seen<=0;begins<=begins+1;
     end
     1:begin
      if(!in_frame||host_data[92:77]!=receiving_generation||host_data[31:16]!=records_seen||host_data[15:0]!=bytes_seen||bytes_seen!=528)$fatal(1,"END counters");
      ends<=ends+1;awaiting_ack<=1;ack_delay<=84000; // 1 ms before PREPARED
     end
     2:$fatal(1,"unexpected ABORT code=%h",host_data[7:0]);
     3:begin
      if(!in_frame||host_data[92:77]!=receiving_generation)$fatal(1,"wrong COMMIT");
      commits<=commits+1;last_generation<=receiving_generation;in_frame<=0;
      host_pause<=commits==0?14280000:3360000; // 170 ms then40 ms
      $display("COMMIT175 number=%0d generation=%0d time_ns=%0t",commits+1,receiving_generation,$time);
     end
     default:$fatal(1,"unknown metadata");
    endcase else begin
     if(!in_frame||host_data[92:77]!=receiving_generation)$fatal(1,"record outside lease");
     records_seen<=records_seen+1;
     if(host_data[95:93]==6)begin
      if(host_data[76:64]!=bytes_seen/16||host_data[11:8]!=bytes_seen%16||host_data[13:12]!=1||host_data[7:0]!=((bytes_seen&255)^((bytes_seen>>8)&255)))$fatal(1,"CHR order/data");
      bytes_seen<=bytes_seen+1;
     end
    end
   end
  end
 end
 always @(posedge clk)if(!reset&&release_frame)begin
  releases<=releases+1;
  if(export_error==2)begin
   if(geometry_valid||!errors[22])$fatal(1,"wrong raster mask rejection");
   rejects<=rejects+1;
  end
 end
 task step(input integer line_no,cycle_no,plane,col,fine);
  begin
   scanline=line_no;dot=cycle_no;bg_low=plane==1;bg_high=plane==2;
   logical_address=col*16+(plane==2?8:0)+fine;physical_address=22'h200000+logical_address;
   ppu_ce=1;@(negedge clk);ppu_ce=0;bg_low=0;bg_high=0;repeat(3)@(negedge clk);
  end
 endtask
 task prefetch(input integer line_no);
  begin step(line_no,326,1,0,(line_no+1)&7);step(line_no,328,2,0,(line_no+1)&7);
   step(line_no,334,1,1,(line_no+1)&7);step(line_no,336,2,1,(line_no+1)&7);end
 endtask
 integer y,x,frames=0,frame_start_ticks=0,nes_ticks=0;
 always @(posedge clk)nes_ticks<=nes_ticks+1;
 initial begin
  repeat(8)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  forever begin
   frames=frames+1;frame_start_ticks=nes_ticks;
   if(owned)held_frames=held_frames+1;
   // After three commits force three rejected acquisitions, then recover.
   display_mask=(commits>=3&&rejects<3)?8'h0e:8'h1e;
   step(7,257,0,0,0);prefetch(7);
   for(y=8;y<232;y=y+1)begin
    step(y,1,0,0,0);
    for(x=2;x<=32;x=x+1)begin step(y,(x-2)*8+6,1,x,y&7);step(y,(x-2)*8+8,2,x,y&7);end
    repeat(40)@(negedge clk);if(y<231)prefetch(y);
   end
   step(232,1,0,0,0);
   // Fixed nominal NES cadence; collector/exporter keep running in the gap.
   while(nes_ticks-frame_start_ticks<357366)@(negedge clk);
  end
 end
 initial begin
  wait(commits==5);repeat(32)@(negedge clk);
  if(begins!=5||ends!=5||rejects<3||held_frames<10||releases<8)$fatal(1,"coverage incomplete");
  $display("PASS LIFECYCLE175 commits=%0d begins=%0d ends=%0d rejects=%0d releases=%0d held_frames=%0d frames=%0d",commits,begins,ends,rejects,releases,held_frames,frames);$finish;
 end
 initial begin #(DROP_RELEASE?150000000:1200000000);$fatal(1,"lifecycle watchdog commits=%0d owned=%b gen=%0d export=%0d errors=%h",commits,owned,generation,exporter.state,errors);end
endmodule
