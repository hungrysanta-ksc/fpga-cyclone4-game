// SPDX-License-Identifier: MIT
// Controlled earliest lease after the REAL capture has recorded its epoch.
// Geometry export is a fixture here. Physical ROM service is a one-edge model.
reg tile_lease=0,plan=0;
wire plan_ready574,request574,out574,done574,fault574,drained574;
wire [21:0] address574;
wire [7:0] data574;
wire [4:0] index574;
reg reply574=0;
reg [21:0] reply_address574;
reg [7:0] reply_data574,rom_pattern574=8'h5a;
integer reads574=0,bytes574=0,first574=-1;
nes_source_tile192 source574(.clk(clk),.reset(local_reset),.stop(1'b0),
 .frame_owned(tile_lease),.geometry_valid(tile_lease),.frame_generation(generation),
 .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),
 .captured_epoch(capture.ownership.capture_epoch),.live_epoch(live_epoch),
 .plan_valid(plan),.plan_ready(plan_ready574),.plan_kind(2'd0),.plan_generation(generation),.plan_slot(10'd1),
 .plan_tag(13'h11),.plan_rows(48'd0),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
 .qualified_slot(1'b1),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
 .mem_ready(!reply574),.mem_response(reply574),.mem_error(1'b0),.mem_response_address(reply_address574),
 .mem_data(reply_data574),.mem_request(request574),.mem_address(address574),
 .out_valid(out574),.out_ready(1'b1),.out_data(data574),.out_index(index574),
 .done(done574),.fault(fault574),.drained(drained574));
always @(posedge clk)begin
 reply574<=0;
 if(local_reset)tile_lease<=0;
 else begin
  if(request574)begin
   if(!source_ready||live_epoch!==capture.ownership.capture_epoch)$fatal(1,"early source request");
   if(first574<0)first574=tick;
   reads574++;
   reply574<=1;reply_address574<=address574;reply_data574<=address574[7:0]^rom_pattern574;
  end
  if(out574)begin
   if(data574!==((index574[0]?8'h18:8'h10)^rom_pattern574))$fatal(1,"stale cache byte");
   bytes574++;
  end
 end
end
task first_tile574(input integer pass,input integer start_at);
 integer before_reads,before_bytes;
 if(pass==2)rom_pattern574=8'ha5;
 first574=-1;
 @(negedge clk);tile_lease=1;
 before_reads=reads574;before_bytes=bytes574;
 while(!plan_ready574)@(negedge clk);
 plan=1;@(negedge clk);plan=0;
 wait(done574);@(negedge clk);
 if(fault574||reads574-before_reads!=2||bytes574-before_bytes!=16)$fatal(1,"first tile consume");
 $display("TILE574 %0d first_request=%0d cache_epoch=%08h",pass,first574-start_at,source574.cache_path.cache.cached_epoch);
 before_reads=reads574;before_bytes=bytes574;
 while(!plan_ready574)@(negedge clk);
 plan=1;@(negedge clk);plan=0;wait(done574);@(negedge clk);
 if(fault574||reads574!=before_reads||bytes574-before_bytes!=16)$fatal(1,"same ROM cache hit");
endtask
