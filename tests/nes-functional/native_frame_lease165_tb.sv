// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Focused lease/raster admission failures; no forced state inside the DUT.
module native_frame_lease165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_frame=0,ppu_ce=0,rom_fault=0;
 reg [8:0] scanline=0,dot=0;
 reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=0,extra_sprites=0;
 reg [1:0] bg_attribute=0;reg [7:0] obj_attribute=0,obj_x=0;
 reg ppu_read=0,ppu_valid=0;reg [13:0] logical_address=0;reg [21:0] physical_address=0;
 reg [14:0] scroll_v=0,scroll_t=0;reg [2:0] fine_x=0,pattern_mode=0;
 reg [7:0] display_mask=8'h1e;reg [191:0] palette=0;reg scroll_access=0;
 reg query=0;reg [2:0] query_kind=0;reg [12:0] query_index=0;reg [15:0] query_generation=0;
 wire owned,geometry_valid,initialized,active,response,hit,scroll_seen;
 wire [15:0] generation;wire [24:0] errors;wire [63:0] data;
 wire [7:0] row_count,object_count,exception_count;wire [5:0] group_count,palette_count;
 reg fill_mode=0,fill_start=0;wire fill_query,fill_request,fill_abort,fill_byte_valid,fill_done,fill_success;
 wire [2:0] fill_query_kind;wire [12:0] fill_query_index,fill_tile;
 wire [15:0] fill_query_generation,fill_generation,fill_byte_generation;
 wire [21:0] fill_address;wire [7:0] fill_byte;wire [3:0] fill_lane;wire [1:0] fill_kind;
 wire [9:0] fill_tiles;wire [13:0] fill_bytes;
 reg fill_response=0;reg [21:0] fill_reply_address;reg [15:0] fill_reply_generation;reg [7:0] fill_reply_data;
 integer joined_bytes=0;
 nes_native_frame165 dut(.query(fill_mode?fill_query:query),.query_kind(fill_mode?fill_query_kind:query_kind),
  .query_index(fill_mode?fill_query_index:query_index),.query_generation(fill_mode?fill_query_generation:query_generation),.*);
 nes_native_fill165 fill(.clk(clk),.reset(reset),.start(fill_start),.clear(release_frame),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .query(fill_query),.query_kind(fill_query_kind),.query_index(fill_query_index),.query_generation(fill_query_generation),
  .response(response),.hit(hit),.data(data),.mem_idle(!fill_response),.mem_ready(1'b1),
  .mem_response(fill_response),.mem_error(1'b0),.mem_response_address(fill_reply_address),
  .mem_response_generation(fill_reply_generation),.mem_data(fill_reply_data),
  .mem_request(fill_request),.mem_abort(fill_abort),.mem_address(fill_address),.mem_generation(fill_generation),
  .byte_valid(fill_byte_valid),.byte_ready(1'b1),.byte_data(fill_byte),.byte_tile(fill_tile),.byte_lane(fill_lane),
  .byte_kind(fill_kind),.byte_generation(fill_byte_generation),.done(fill_done),.success(fill_success),
  .tile_count(fill_tiles),.byte_count(fill_bytes));
 integer checks=0,scenes=0,rejects=0,y,x,mode;reg [15:0] old_generation;
 task check(input bit condition,input string why);
  begin checks=checks+1;if(!condition)$fatal(1,"%s gen=%0d valid=%0d err=%h",why,generation,geometry_valid,errors);end
 endtask
 always @(posedge clk)begin
  fill_response<=fill_request;
  if(fill_request)begin
   fill_reply_address<=fill_address;fill_reply_generation<=fill_generation;
   fill_reply_data<=fill_address[7:0]^fill_address[15:8];
  end
  if(fill_byte_valid)begin
   check(fill_mode&&fill_byte_generation==generation&&fill_kind==1,"joined fill generation/kind");
   check(fill_tile==joined_bytes/16 && fill_lane==joined_bytes%16,"joined required set stream");
   check(fill_byte==((joined_bytes&255)^((joined_bytes>>8)&255)),"joined memory byte");
   joined_bytes=joined_bytes+1;
  end
 end
 task step(input integer line_no,input integer cycle_no,input integer plane,input integer col,input integer fine);
  begin
   scanline=line_no;dot=cycle_no;bg_low=plane==1;bg_high=plane==2;
   ppu_read=plane!=0;ppu_valid=ppu_read;
   logical_address=col*16+(plane==2?8:0)+fine;physical_address=22'h200000+logical_address;
   ppu_ce=1;@(negedge clk);ppu_ce=0;bg_low=0;bg_high=0;ppu_read=0;
   repeat(3)@(negedge clk);
  end
 endtask
 task prefetch(input integer line_no);
  begin
   step(line_no,326,1,0,(line_no+1)&7);step(line_no,328,2,0,(line_no+1)&7);
   step(line_no,334,1,1,(line_no+1)&7);step(line_no,336,2,1,(line_no+1)&7);
  end
 endtask
 task drop;
  begin release_frame=1;@(negedge clk);release_frame=0;query=0;rom_fault=0;
   check(!owned&&!geometry_valid&&!response&&!hit,"release clears lease");
   wait(initialized);@(negedge clk);
  end
 endtask
 task read_item(input integer kind,input integer index,input integer gen,input bit expect_hit);
  begin
   query=1;query_kind=kind;query_index=index;query_generation=gen;@(negedge clk);
   check(response&&hit===expect_hit&& (expect_hit||data==0),"query gating");
   query=0;@(negedge clk);check(!response&&!hit&&data==0,"no stale response");
  end
 endtask
 task scene(input integer fault_mode);
  begin
   display_mask=fault_mode==2?8'h0e:8'h1e;fine_x=0;palette=0;scroll_access=0;
   step(7,257,0,0,0);scenes=scenes+1;prefetch(7);
   for(y=8;y<232;y=y+1)begin
    if(fault_mode==3 && y==32)palette[11:6]=1;
    if(fault_mode==3 && y==64)palette[17:12]=2;
    if(fault_mode==4 && y==32)palette[5:0]=1;
    if(fault_mode==6 && y==32)palette[11:6]=1;
    step(y,1,0,0,0);
    for(x=2;x<=32;x=x+1)begin
     step(y,(x-2)*8+6,1,x,y&7);
     if(!(fault_mode==5 && y==20 && x==2))step(y,(x-2)*8+8,2,x,y&7);
    end
    if(y==20)begin
     if(fault_mode==1)fine_x=1;
     scroll_v=15'h1123;scroll_t=15'h2456;scroll_access=1;step(y,255,0,0,0);scroll_access=0;
     fine_x=0;
    end
    // Preserve more than the 33 copy clocks between the last visible BG
    // pair and the following line's prefetch; do not compress that gap away.
    repeat(40)@(negedge clk);
    if(y<231)prefetch(y);
   end
   step(232,1,0,0,0);repeat(10)@(negedge clk);
   check(owned,"all members retire");
   check(geometry_valid== (fault_mode==0||fault_mode==6),"admission");
   if(fault_mode>0 && fault_mode<6)begin
    rejects=rejects+1;check(errors!=0,"rejection has cause");read_item(0,0,generation,0);
   end else begin
    check(errors==0&&scroll_seen&&row_count==224&&group_count==28,"complete geometry permits v/t access");
    check(palette_count==(fault_mode==6?2:1),"palette count");
    read_item(0,0,generation,1);read_item(0,28*33,generation,0);
    read_item(1,223,generation,1);read_item(1,224,generation,0);
    read_item(4,223,generation,1);read_item(4,224,generation,0);
    read_item(5,palette_count*32-1,generation,1);read_item(5,palette_count*32,generation,0);
    read_item(6,32,generation,1);read_item(6,8191,generation,1);
    read_item(7,0,generation,0);read_item(0,0,generation-1,0);
   end
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  // Fault before raster row8, with PPU CE stopped. Recovery must not compare
  // the private raster generation against the required-set generation.
  step(7,257,0,0,0);old_generation=generation;rom_fault=1;repeat(3)@(negedge clk);
  check(owned&&!geometry_valid&&errors[24],"pre-row8 fault cannot deadlock");rejects=rejects+1;
  read_item(6,0,generation,0);drop();scene(0);
  check(generation==old_generation+1,"one public generation after early fault");
  // Cancel a simultaneous query. Its response/data must not escape release.
  query=1;query_kind=0;query_index=0;query_generation=generation;release_frame=1;
  @(negedge clk);check(!response&&!hit&&data==0&&!owned,"release wins query");
  release_frame=0;query=0;wait(initialized);@(negedge clk);
  for(mode=1;mode<=6;mode=mode+1)begin scene(mode);drop();end
  scene(0);query=1;query_kind=0;query_generation=generation;reset=1;
  @(negedge clk);check(!response&&!hit&&data==0&&!owned&&generation==0,"reset wins query");
  query=0;reset=0;wait(initialized);@(negedge clk);scene(0);
  fill_mode=1;fill_start=1;@(negedge clk);fill_start=0;wait(fill_done);@(negedge clk);
  check(fill_success && fill_tiles==33 && fill_bytes==528 && joined_bytes==528,"direct sealed frame to fill");fill_mode=0;
  rom_fault=1;@(negedge clk);check(owned&&!geometry_valid&&errors[24],"fault revokes sealed lease");
  check(!fill_success,"source fault also revokes completed fill");
  read_item(0,0,generation,0);rejects=rejects+1;drop();
  $display("PASS FRAMELEASE165 checks=%0d scenes=%0d rejects=%0d",checks,scenes,rejects);$finish;
 end
 initial begin #20000000;$fatal(1,"lease watchdog");end
endmodule
