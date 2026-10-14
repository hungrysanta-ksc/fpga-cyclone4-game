// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_clip178_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ppu_ce=0,release_packet=0,query=0;
 reg [8:0] scanline=0,dot=0;
 reg [7:0] display_mask=8'h1e;
 reg source_fault=0;
 wire owned,valid,response,hit;wire [7:0] errors,row_count;
 wire [55:0] data;integer checks=0,frames=0;
 nes_native_raster_frame165 dut(.clk(clk),.reset(reset),.ppu_ce(ppu_ce),
 .scanline(scanline),.dot(dot),.scroll_v(15'd0),.scroll_t(15'd0),
 .fine_x(3'd0),.pattern_mode(3'd0),.display_mask(display_mask),.palette(192'd0),
 .scroll_access(1'b0),.source_fault(source_fault),.release_packet(release_packet),
 .query(query),.query_palette(1'b0),.query_row(8'd223),.query_bank(5'd0),.query_color(5'd0),
 .owned(owned),.valid(valid),.errors(errors),.row_count(row_count),.response(response),.hit(hit),.data(data),
 .scroll_seen(),.generation(),.palette_count());
 task check(input bit ok,input string name);
  begin checks++;if(!ok)$fatal(1,"CLIP178 %s",name);end
 endtask
 task step(input integer line,input integer x);
  begin @(negedge clk);scanline=line;dot=x;ppu_ce=1;
   @(posedge clk);#1;@(negedge clk);ppu_ce=0;end
 endtask
 task release_it;
  begin @(negedge clk);release_packet=1;@(posedge clk);#1;
   check(!owned&&!valid&&!dut.active,"release");@(negedge clk);release_packet=0;end
 endtask
 task frame(input integer mask,input integer variant);
  integer y;begin
   for(y=0;y<224;y++)begin
    display_mask=mask;
    if(variant==1&&y>=112)display_mask=8'h18;
    if(variant==2&&y>=112)display_mask=8'h1e;
    step(y+8,1);repeat(35)@(negedge clk);
    if(variant==3&&y==100)display_mask=8'h18;
    step(y+8,128);
   end
   step(232,1);frames++;check(owned&&row_count==224,"sealed complete rows");
   if(variant==0&&(mask==8'h18||mask==8'h1e))begin
    check(valid&&errors==0,"supported uniform mask");
    @(negedge clk);query=1;@(posedge clk);#1;
    check(response&&hit&&data[43:36]==mask,"preserved mask in row");
    @(negedge clk);query=0;
   end else begin
    check(!valid,"unsupported frame withheld");
    if(variant==3)check(errors[3],"midline change remains rejected");
    else check(errors[6],"mask cause remains explicit");
   end
   release_it();
  end
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;
  for(integer m=0;m<256;m++)frame(m,0);
  frame(8'h1e,1);frame(8'h18,2);frame(8'h1e,3);
  frame(8'h18,0);frame(8'h1e,0);
  step(8,1);source_fault=1;repeat(3)@(negedge clk);
  check(owned&&!valid&&errors[5],"fault still retires");source_fault=0;release_it();
  frame(8'h18,0);
  $display("PASS CLIP178 frames=%0d checks=%0d",frames,checks);$finish;
 end
 initial begin #30000000;$fatal(1,"CLIP178 watchdog");end
endmodule
