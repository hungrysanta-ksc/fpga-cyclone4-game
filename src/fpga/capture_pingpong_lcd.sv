// Capture-side integration candidate. Word addresses are logical PSRAM addresses.
// Shared RGB epoch map: 400000..407fff. Frame 0 IDs/dictionary: 408000/40c000.
// Frame 1 IDs/dictionary: 418000/41c000. No frame copy and no second epoch map.
// Consumer holds bank_ready until its LAST memory response, then pulses release.
// start is a one-shot before the first source pixel; wait for armed at startup.
module capture_pingpong_lcd(
 input wire clk,reset,start,lcd_on,pixel_valid,input wire[14:0]pixel_rgb,
 input wire[1:0]bank_release,
 output reg[1:0]bank_ready,
 output reg[8:0]bank0_colors,bank1_colors,
 output wire armed,output reg error,output reg[2:0]error_code,
 output wire req_valid,req_write,input wire req_ready,
 output wire[22:0]req_addr,output wire[15:0]req_data,
 input wire rsp_valid,input wire[15:0]rsp_data,
 output wire[6:0]fifo_level
);
 reg running,launch,waiting,write_bank,lcd_previous;
 reg[14:0]source_pixels;
 wire cancelled;
 wire abort_frame=running&&lcd_previous&&!lcd_on&&source_pixels!=0;
 wire active,done,cap_error,busy;
 wire[1:0]cap_code;
 wire[8:0]colors;
 wire[16:0]byte_addr;
 assign armed=active&&!error;
 // Only frame storage is banked. The single capture engine retains its epoch
 // and sweep state across frames, so its lookup map must remain shared.
 assign req_addr=23'h400000+{7'b0,byte_addr[16:1]}+
                 ((write_bank&&byte_addr[16])?23'h010000:23'd0);
 rgb_capture64_abort engine(clk,reset,launch,abort_frame,cancelled,pixel_valid&&lcd_on&&running&&!error,
  pixel_rgb,active,req_valid,req_write,req_ready,byte_addr,req_data,
  rsp_valid,rsp_data,colors,done,cap_error,cap_code,busy,fifo_level);
 always @(posedge clk) begin
  if(reset) begin
   source_pixels<=0;lcd_previous<=0;running<=0;launch<=0;waiting<=0;write_bank<=0;bank_ready<=0;
   bank0_colors<=0;bank1_colors<=0;error<=0;error_code<=0;
  end else begin
   launch<=0;lcd_previous<=lcd_on;
   if(!lcd_on)source_pixels<=0;
   else if(pixel_valid&&running)source_pixels<=source_pixels==23039?15'd0:source_pixels+1'b1;
   bank_ready<=bank_ready&~bank_release;
   if(start&&!running&&!error)begin running<=1;launch<=1;end
   if(running&&!error)begin
    if(cancelled)begin waiting<=1;end
    else if(done)begin
     bank_ready[write_bank]<=1;
     if(write_bank)bank1_colors<=colors;else bank0_colors<=colors;
     write_bank<=!write_bank;waiting<=1;
    end else if(waiting&&(!bank_ready[write_bank]||bank_release[write_bank]))begin
     launch<=1;waiting<=0;
    end
    if(pixel_valid&&lcd_on&&!active)begin error<=1;error_code<=3;end
    if(cap_error)begin error<=1;error_code<={1'b0,cap_code};end
    // Releasing an unpublished bank is a consumer protocol error.
    if(|(bank_release&~bank_ready))begin error<=1;error_code<=4;end
   end
  end
 end
endmodule
