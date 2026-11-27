// Display-mask admission and the encoded 224-row opening seen by the ARM.
`timescale 1ns/1ps
module ff3_mask1045_tb;
 reg clk=0;
 always #5 clk=!clk;
 reg rst=1,begin_packet=0,end_packet=0,ce=0,commit=0,query=0;
 reg [7:0] mask=0,row=0;
 reg [8:0] dot=0;
 wire patch,valid,hit;
 wire [55:0] data;
 `ifdef FF3_BACKDROP
 reg non_backdrop=1;
 `endif
 nes_native_raster181 raster(
  `ifdef FF3_BACKDROP
  .non_backdrop(non_backdrop),
  `endif.clk(clk),.reset(rst),.release_packet(1'b0),.source_fault(1'b0),
  .begin_packet(begin_packet),.end_packet(end_packet),.ppu_ce(ce),.dot(dot),.scanline(9'd8+row),
  .display_mask(mask),.palette(192'h36),.fine_x(3'b0),.scroll_v(15'd0),.scroll_t(15'd0),.pattern_mode(3'd0),
  .scroll_access(1'b0),.row_commit(commit),.committed_row(row),.row_patched(1'b0),.row_slot(3'd0),
  .row_needs_patch(patch),.query(query),.query_palette(1'b0),.query_row(row),.query_bank(5'd0),
  .query_color(5'd0),.hit(hit),.data(data),.valid(valid));
 task begin_capture;
  rst=1;@(negedge clk);rst=0;begin_packet=1;@(negedge clk);begin_packet=0;
 endtask
 task start_row;
  dot=1;ce=1;@(negedge clk);dot=0;ce=0;
 endtask
 reg expected;
 initial begin
  @(negedge clk);
  for(int m=0;m<256;m++)begin
   mask=m;row=0;begin_capture();start_row();
   expected=
   `ifndef FF3_GRAYSCALE
    !mask[0] &&
   `endif
    !mask[7:5] && mask[3] && (!mask[4] || mask[1]==mask[2]);
   if(patch!==!expected)$fatal(1,"mask %h",mask);
  end
  `ifdef FF3_BACKDROP
  mask=8'h10;row=0;
  non_backdrop=0;begin_capture();start_row();if(patch!==0)$fatal(1,"uniform sprite-only row");
  non_backdrop=1;#1;if(patch!==1)$fatal(1,"visible sprite escaped raw path");
  `endif
  mask=8'h0a;begin_capture();
  for(int y=0;y<224;y++)begin
   row=y;start_row();if(patch)$fatal(1,"opening row %d",y);
   repeat(34)@(negedge clk);commit=1;@(negedge clk);commit=0;
  end
  end_packet=1;@(negedge clk);end_packet=0;
  if(valid!==1'b1)$fatal(1,"opening frame rejected");
  for(int y=0;y<224;y++)begin
   row=y;query=1;@(negedge clk);
   // Bits 40:36 encode OBJ enable, BG enable, the two left edges, and grayscale.
   if(!hit || data[40:36]!==5'b01110 || data[49])$fatal(1,"opening row descriptor %d %h",y,data);
  end
  $display("PASS FF3 mask 256 cases and 224 ordinary BG-only opening rows");$finish;
 end
endmodule
