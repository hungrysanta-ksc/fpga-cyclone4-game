// Frame lease and effective palette as consumed by the renderer.
`timescale 1ns/1ps
module ff3_battle1047_tb;
 reg clk=0,reset=1,changed=0,start=0,retire=0,discard=0;
 reg [2:0] changed_page=3;
 reg [15:0] issued=0,ack=0;
 wire ready,unchanged;
 always #5 clk=!clk;
 nes_chr_snapshot snap(.clk(clk),.reset(reset),.changed(changed),.changed_page(changed_page),
   .start(start),.collecting(1'b0),.retire(retire),.discard(discard),.start_gen(issued),
   .retire_gen(ack),.frame_unchanged(unchanged),.can_start(ready),.scan_data(8'd0),
   .read_req(1'b0),.cancel(1'b0),.read_addr(18'd0),.read_gen(16'd0),.ram_q(8'd0));
 task capture(input bit expected);
  wait(ready);@(negedge clk);start=1;issued++;@(negedge clk);start=0;
  if(unchanged!==expected)$fatal(1,"bad CHR history generation=%d expected=%b",issued,expected);
 endtask
 task finish_capture(input bit cancel,input bit last_write);
  discard=cancel;retire=!cancel;ack=issued;changed=last_write;
  @(negedge clk);retire=0;discard=0;changed=0;@(negedge clk);
 endtask
 reg begin_packet=0,end_packet=0,ce=0,commit=0,query=0;
 reg [7:0] mask=0,row=0;
 reg [8:0] dot=0;
 reg [4:0] index=0;
 reg [191:0] pal=0;
 wire patch,valid,hit;wire [55:0] data;
 nes_native_raster181 raster(.clk(clk),.reset(reset),.release_packet(1'b0),.source_fault(1'b0),
   .non_backdrop(1'b1),.begin_packet(begin_packet),.end_packet(end_packet),.ppu_ce(ce),
   .dot(dot),.scanline(9'd8+row),.display_mask(mask),.palette(pal),.fine_x(3'd0),.scroll_v(15'd0),
   .scroll_t(15'd0),.pattern_mode(3'd0),.scroll_access(1'b0),.row_commit(commit),.committed_row(row),
   .row_patched(1'b0),.row_slot(3'd0),.row_needs_patch(patch),.query(query),.query_palette(1'b1),
   .query_row(row),.query_bank(5'd0),.query_color(index),.hit(hit),.data(data),.valid(valid));
 integer capture_colors=0;
 task frame(input bit grey);
  reset=1;@(negedge clk);reset=0;begin_packet=1;@(negedge clk);begin_packet=0;
  mask=grey?'h1f:'h1e;
  for(int y=0;y<224;y++)begin
   row=y;dot=1;ce=1;@(negedge clk);dot=0;ce=0;if(patch)$fatal(1,"uniform mask rejected");
   commit=1;@(negedge clk);commit=0;repeat(34)@(negedge clk);
  end
  end_packet=1;@(negedge clk);end_packet=0;if(!valid)$fatal(1,"frame rejected");
  for(int i=0;i<32;i++)begin index=i;query=1;@(negedge clk);
   if(capture_colors)$fwrite(capture_colors,"%02x ",data[7:0]);
   if(!hit || data!==(pal[i*6+:6]&(grey?6'h30:6'h3f)))$fatal(1,"wrong effective color %d %d",grey,i);
  end
  if(capture_colors)$fdisplay(capture_colors,"");
  query=0;
 endtask
 reg [7:0] reference[0:64*33-1];
 initial begin
  repeat(4)@(negedge clk);reset=0;
  capture(0);finish_capture(0,0);capture(1);finish_capture(0,1);
  capture(0);finish_capture(1,0);capture(0);finish_capture(0,0);
  capture(1);changed=1;@(negedge clk);changed=0;
  retire=1;ack=issued-1;@(negedge clk);retire=0;if(ready)$fatal(1,"wrong retirement");
  finish_capture(0,0);capture(0);finish_capture(0,0);capture(1);finish_capture(0,0);
  `ifdef FF3_PAGE_HISTORY
  for(int page=0;page<8;page++)begin
   changed_page=page;changed=1;@(negedge clk);changed=0;
   capture(0);
   if(snap.clean_pages!==(8'hff^(8'b1<<page)))$fatal(1,"page %d mask %h",page,snap.clean_pages);
   changed_page=(page+1)%8;finish_capture(0,1);capture(0);
   if(snap.clean_pages!==(8'hff^(8'b1<<changed_page)))$fatal(1,"write on ACK");
   finish_capture(1,0);capture(0);
   if(snap.clean_pages!==(8'hff^(8'b1<<changed_page)))$fatal(1,"discard lost write");
   finish_capture(0,0);capture(1);finish_capture(0,0);
  end
  $display("PASS eight page masks, ACK-edge writes and discard");
  `endif
  for(int i=0;i<32;i++)pal[i*6+:6]=(13*i+15)%64;
  frame(0);frame(1);frame(0);
  if ($test$plusargs("reference")) begin
   $readmemh("flash.hex",reference);
   capture_colors=$fopen("effective.hex","w");if(!capture_colors)$fatal(1,"palette output");
   for(int f=0;f<64;f++) begin
    if(reference[33*f] !== (f%2==0 ? 8'h1f : 8'h1e))$fatal(1,"unexpected reference mask");
    for(int i=0;i<32;i++)pal[i*6+:6]=reference[33*f+i+1];
    frame(reference[33*f][0]);
   end
   $fclose(capture_colors);capture_colors=0;
   $display("PASS FF3 64 reference flash frames, 224 rows and all 32 effective palette entries per frame");
  end
  reset=1;@(negedge clk);reset=0;capture(0);
  $display("PASS FF3 battle palettes and CHR history: same image, dirty ACK edge, discard, wrong token, reset");$finish;
 end
endmodule
