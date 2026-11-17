// Replay the visible PPUMASK edge of reference frame 1557 and a title control.
// Drive a constant palette, legal row cadence and all pixels. Only PPUMASK varies.
`timescale 1ns/1ps
module mask820_dots_tb;
 reg clk=0, reset=1, start_frame=0, finish=0, ce=0;
 always #5 clk=~clk;
 reg [8:0] line_no=0,dot=0;
 reg [7:0] mask=8'h1e;
 wire raw,commit,patched,patch_valid,raster_valid;
 wire [7:0] committed,patch_errors,raster_errors,raster_rows;
 wire [2:0] slot,count;
 wire [8:0] row_id=line_no-9'd8, px=dot-9'd2;
 nes_native_raster181 raster(.clk(clk),.reset(reset),.release_packet(1'b0),
   .begin_packet(start_frame),.end_packet(finish),.ppu_ce(ce),.source_fault(1'b0),
   .scanline(line_no),.dot(dot),.scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),
   .pattern_mode(3'd0),.display_mask(mask),.palette(192'd0),.scroll_access(1'b0),
   .row_commit(commit),.row_patched(patched),.committed_row(committed),.row_slot(slot),
   .row_needs_patch(raw),.query(1'b0),.query_palette(1'b0),.query_row(8'd0),
   .query_bank(5'd0),.query_color(5'd0),.valid(raster_valid),.errors(raster_errors),.row_count(raster_rows));
 nes_patch_rows181 patches(.clk(clk),.reset(reset),.release_frame(1'b0),
   .begin_frame(start_frame),.end_frame(finish),.source_fault(1'b0),.generation_in(16'd1),
   .row_start(ce && dot==1),.row_end(ce && dot==258),.pixel_valid(ce && dot>=2 && dot<=257),
   .need_patch(ce && dot==258 && raw),.row_index(row_id[7:0]),.pixel_x(px[7:0]),.pixel_color(px[5:0]),
   .query(1'b0),.query_generation(16'd0),.query_slot(3'd0),.query_x(8'd0),
   .valid(patch_valid),.errors(patch_errors),.count(count),.row_commit(commit),.row_patched(patched),
   .committed_row(committed),.row_slot(slot));
 task automatic check_frame(input int split_dot);
   integer y,x,requested,first_over;
   begin
     reset=1;ce=0;mask=8'h1e;@(negedge clk);reset=0;start_frame=1;
     @(negedge clk);start_frame=0;ce=1;requested=0;first_over=-1;
     for(y=8;y<232;y=y+1) for(x=0;x<341;x=x+1) begin
       line_no=y;dot=x;
       if(y==192 && x==split_dot)mask=8'h0e;
       @(negedge clk);
       if(commit && patched) begin requested=requested+1;if(committed!=184)$fatal(1,"wrong raw row");end
       if(patch_errors[3] && first_over<0)first_over=y;
     end
     ce=0;finish=1;@(negedge clk);finish=0;
     if(!raster_valid || raster_errors!=0 || raster_rows!=224) $fatal(1,"raster");
     if(split_dot<0)begin
       if(!patch_valid || patch_errors!=0 || requested!=0) $fatal(1,"title");
     end else if(!patch_valid || patch_errors!=0 || count!=1 || requested!=1 || first_over!=-1)
       $fatal(1,"split mismatch count=%d requested=%d first=%d error=%h",count,requested,first_over,patch_errors);
     $display("MASK820 dot=%0d requested=%0d first_over=%0d errors=%h valid=%b",split_dot,requested,first_over,patch_errors,patch_valid);
   end
 endtask
 initial begin
   @(negedge clk);check_frame(-1);for(int d=91;d<=108;d=d+1)check_frame(d);check_frame(-1);
   $display("PASS820 mask replay");$finish;
 end
endmodule

