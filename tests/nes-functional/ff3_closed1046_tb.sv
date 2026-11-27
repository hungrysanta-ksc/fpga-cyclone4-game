// Exercise completed PPU rows and query the actual compact/raster/raw RAM ports.
`timescale 1ns/1ps
module ff3_closed1046_tb;
 reg clk=0,reset=1,release_frame=0,ce=0,query=0;
 always #5 clk=!clk;
 reg [8:0] line=0,dot=0;
 reg [5:0] color=15;
 reg [2:0] kind=0;reg [13:0] index=0;
 wire init,owned,valid,hit;wire [15:0] gen;
 wire [5:0] groups;wire [2:0] slots;wire [63:0] data;
 nes_native_frame201 dut(.clk(clk),.reset(reset),.release_frame(release_frame),.ppu_ce(ce),
  .rom_fault(1'b0),.snapshot_conflict(1'b0),.scanline(line),.dot(dot),.color(color),.emphasis(3'd0),
  .bg_low(1'b0),.bg_high(1'b0),.obj_low(1'b0),.obj_high(1'b0),.obj_valid(1'b0),.extra_sprites(1'b0),
  .bg_attribute(2'd0),.obj_attribute(8'd0),.obj_x(8'd0),.ppu_read(1'b0),.ppu_valid(1'b0),
  .logical_address(14'd0),.physical_address(22'd0),.scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),
  .pattern_mode(3'd0),.display_mask(8'd0),.palette(192'h0f),.scroll_access(1'b0),.query(query),
  .query_kind(kind),.query_index(index),.query_generation(gen),.initialized(init),.owned(owned),
  .geometry_valid(valid),.hit(hit),.data(data),.generation(gen),.group_count(groups),.patch_count(slots));
 task read_word(input int k,input int addr,input logic [63:0] expected);
  kind=k;index=addr;query=1;@(negedge clk);
  if(hit!==1 || data!==expected)$fatal(1,"bad query %d/%d got %h hit %b",k,addr,data,hit);
  query=0;@(negedge clk);
 endtask
 task frame(input int ink);
  wait(init);@(negedge clk);
  for(int l=7;l<=232;l++)for(int d=0;d<341;d++)begin
   // The PPU increments its coordinate on CE. The pixel bus settles one clock later.
   ce=1;@(negedge clk);dot=d;line=l;color=(l>=8 && l<8+ink && d==257)?6'd33:6'd15;
   ce=0;repeat(3)@(negedge clk);
  end
  if(owned!==1 || valid!==(ink<=7))$fatal(1,"wrong admission ink=%d err=%h raw=%h raster=%h",
    ink,dut.errors,dut.patch_errors,dut.raster_errors);
  if(valid)begin
   if(groups!=1 || slots!=ink)$fatal(1,"group / slot count");
   for(int i=0;i<33;i++)read_word(0,i,0);
   for(int y=0;y<224;y++)begin
    read_word(1,y,0);read_word(4,y,y<ink?((64'h2|(y<<2))<<48):0);
   end
   read_word(5,0,15);
   for(int j=0;j<ink;j++)for(int x=0;x<256;x++)read_word(7,j*256+x,x==255?33:15);
  end
  release_frame=1;@(negedge clk);release_frame=0;@(negedge clk);
 endtask
 initial begin
  repeat(4)@(negedge clk);reset=0;
  frame(0);frame(1);frame(8);reset=1;@(negedge clk);reset=0;frame(0);
  $display("PASS forced blank, 33 checked zero map words, 224 raster rows, last pixel, overflow, cold restart");$finish;
 end
endmodule
