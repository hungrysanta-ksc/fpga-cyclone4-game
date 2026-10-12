// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_fetch165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_scene=0,ppu_ce=0,rom_fault=0;
 reg [8:0] scanline=0,dot=0;
 reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=1,extra_sprites=0;
 reg [1:0] bg_attribute=0;reg [7:0] obj_attribute=0,obj_x=0;
 reg ppu_read=1,ppu_valid=1;reg [13:0] logical_address=0;
 wire [21:0] physical_address;
 reg query=0;reg [12:0] query_tile=0;
 wire initialized,active,owned,valid,event_valid,response;
 wire [7:0] errors;wire [15:0] generation;wire [63:0] event_data;wire [1:0] required_kind;
 nes_native_fetch165 dut(.*);
 reg cart_ce=0,cart_write=0;reg [15:0] cart_addr=0;reg [7:0] cart_data=0;
 cart_top mapper(.clk(clk),.ce(cart_ce),.cpu_ce(cart_ce),.reset(reset),.paused(1'b0),
  .game158_preview_write(1'b0),.game148_hint_logic(14'd0),.flags(64'd4),
  .prg_ain(cart_addr),.prg_read(1'b0),.prg_write(cart_write),.prg_din(cart_data),.prg_from_ram(8'd0),
  .prg_mask(21'h3ffff),.chr_mask(20'h1ffff),.chr_ain_orig(logical_address),.chr_ain_ex(14'd0),
  .chr_ex(1'b0),.chr_read(ppu_read),.chr_write(1'b0),.chr_din(8'd0),.chr_aout(physical_address),.audio_in(16'd0));
 integer checks=0,events=0,pixels=0,rejects=0,i,j,k;
 reg [1:0] expected[0:8191];
 task check(input bit ok,input string why);
  begin checks++;if(!ok)$fatal(1,"fetch165 %s line=%0d dot=%0d errors=%h",why,scanline,dot,errors);end
 endtask
 task idle(input integer n);begin repeat(n)@(negedge clk);end endtask
 task write_reg(input [15:0] a,input [7:0] b);
  begin @(negedge clk);cart_ce=1;cart_write=1;cart_addr=a;cart_data=b;
   @(negedge clk);cart_ce=0;cart_write=0;end
 endtask
 task clear_flags;begin bg_low=0;bg_high=0;obj_low=0;obj_high=0;end endtask
 task marker(input integer y,input integer x);
  begin @(negedge clk);clear_flags();ppu_ce=1;scanline=y;dot=x;
   @(negedge clk);ppu_ce=0;end
 endtask
 task begin_it;
  begin while(!initialized)@(negedge clk);marker(7,257);check(active,"preceding-line capture armed");end
 endtask
 task release_it;
  begin @(negedge clk);release_scene=1;query=1;
   @(posedge clk);#1;check(!response && !owned && !event_valid,"release cancels query and event");
   @(negedge clk);release_scene=0;query=0;clear_flags();rom_fault=0;extra_sprites=0;ppu_valid=1;
   for(integer t=0;t<8192;t++)expected[t]=0;
  end
 endtask
 task seal(input bit good);
  begin marker(232,1);idle(5);check(owned && valid==good,"sealed set validity");end
 endtask
 task ask(input integer tile,input [1:0] want);
  begin @(negedge clk);query=1;query_tile=tile;
   @(posedge clk);#1;check(response && required_kind===want,"physical tile membership");
   @(negedge clk);query=0;end
 endtask
 task half(input bit obj,input bit high,input integer line,input integer cycle,input [13:0] a);
  begin @(negedge clk);ppu_ce=1;scanline=line;dot=cycle;logical_address=a;
   bg_low=!obj&&!high;bg_high=!obj&&high;obj_low=obj&&!high;obj_high=obj&&high;
   @(posedge clk);#1;
   @(negedge clk);ppu_ce=0;clear_flags();end
 endtask
 task tile(input bit obj,input integer line,input integer lowdot,input [13:0] a,input integer col,input integer rank);
  reg [21:0] phys;reg [63:0] want;integer row;begin
   half(obj,0,line,lowdot,a);phys=physical_address;
   half(obj,1,line,lowdot+2,a|14'd8);
   row=(obj || lowdot>=321)?line+1-8:line-8;
   want={11'd0,rank[2:0],obj,(obj?obj_attribute:{6'd0,bg_attribute}),col[7:0],row[7:0],a[12:4],a[2:0],phys[16:4]};
   check(event_valid && event_data===want,"actual mapped tag / destination / attributes");events++;
   expected[phys[16:4]]|=obj?2'b10:2'b01;
  end
 endtask

 // Pixel-coordinate control uses the unmodified BgPainter pipeline. Its data
 // comes from different per-column patterns; comparison is at the visible-dot
 // sampling edge, including both previous-line prefetches and all fine-Xs.
 reg bg_ce=0,bg_enable=0,bg_clear=1;
 reg [8:0] bg_dot=0;reg [2:0] fine_x=0;reg [7:0] bg_data=0;
 wire [3:0] bg_pixel;
 BgPainter actual_bg(.clk(clk),.pclk0(bg_ce),.clear(bg_clear),.enable(bg_enable),
  .latch_nametable(1'b0),.latch_attrtable(1'b0),.latch_pattern1(bg_dot[2:0]==6),
  .latch_pattern2(bg_dot[2:0]==0),.fine_x_scroll(fine_x),.vram_v(15'd0),.vram_data(bg_data),.pixel(bg_pixel));
 function automatic [7:0] pattern(input integer col,input bit plane);
  pattern=plane?((col*53+8'h69)&255):((col*29+8'h93)&255);
 endfunction
 task bg_step(input integer d,input bit visible);
  integer col,x,index;reg [7:0] lo,hi;begin
   @(negedge clk);bg_ce=1;bg_dot=d;bg_enable=(d>=1 && d<=256)||(d>=321 && d<=336);
   col=(d>=321)?((d>=329)?1:0):((d+7)/8+1);
   bg_data=pattern(col,d[2:0]==0);
   if(visible)begin
    x=d-1;index=(x+fine_x)/8;lo=pattern(index,0);hi=pattern(index,1);
    #1;check(bg_pixel[1:0]=={hi[7-((x+fine_x)%8)],lo[7-((x+fine_x)%8)]},"BG fetch column to actual pixel pipeline");pixels++;
   end
   @(negedge clk);bg_ce=0;
  end
 endtask
 // Actual sprite sequencer: observations latch the same attr/X source bytes
 // as SpriteSet. Its address computes the selected 8x16 half and flipped row.
 reg spr_ce=0,spr_enabled=0,spr_range=1,spr_size=0,spr_table=0;
 reg [8:0] spr_line=20;reg [7:0] spr_temp=0,spr_data=8'h96;
 wire [12:0] spr_addr;wire [3:0] spr_load;wire [26:0] spr_load_data;
 wire spr_valid;wire [7:0] spr_attribute,spr_x;
 SpriteAddressGen actual_sprite(.clk(clk),.ce(spr_ce),.enabled(spr_enabled),.rendering(1'b1),
  .obj_size(spr_size),.obj_patt(spr_table),.in_range(spr_range),.scanline(spr_line),
  .temp(spr_temp),.vram_data(spr_data),.vram_addr(spr_addr),.load(spr_load),.load_in(spr_load_data),
  .native_valid(spr_valid),.native_attribute(spr_attribute),.native_x(spr_x));
 task spr_step(input integer phase,input integer tileid,input integer attr);
  begin @(negedge clk);spr_ce=1;spr_enabled=1;
   case(phase)0:spr_temp=12;1:spr_temp=tileid;2:spr_temp=attr;3:spr_temp=237;default:spr_temp=0;endcase
   @(negedge clk);spr_ce=0;end
 endtask
 initial begin
  for(i=0;i<8192;i++)expected[i]=0;
  idle(4);reset=0;
  // Distinct banks, odd 2KiB writes and MMC3 inversion use real mapper logic.
  for(i=0;i<6;i++)begin write_reg(16'h8000,i);write_reg(16'h8001,17+i*13);end
  begin_it();bg_attribute=2;obj_attribute=8'he3;obj_x=237;
  tile(1,7,262,14'h1045,237,0);
  tile(0,7,326,14'h0125,0,0);tile(0,7,334,14'h0145,1,0);
  for(i=0;i<31;i++)tile(0,8,6+i*8,(i*16)&14'h0ff7,i+2,0);
  // Same logical tile, two physical banks in this capture; neither may vanish.
  tile(0,9,6,14'h1041,2,0);
  write_reg(16'h8000,2);write_reg(16'h8001,91);
  tile(0,10,6,14'h1041,2,0);
  for(i=0;i<8;i++)tile(0,11,6+i*8,(i*1024)+3,i+2,0);
  write_reg(16'h8000,8'h80);
  for(i=0;i<8;i++)tile(1,11,262+i*8,(i*1024)+3,237,i);
  // Both kinds can require one physical tile, and adjacent requests may target
  // the same metadata word. Membership is physical, not the last logical bank.
  tile(0,12,6,14'h1043,2,0);tile(1,12,262,14'h1043,237,0);
  // Dummy/outside-crop fetches must not produce descriptors or extra tiles.
  obj_valid=0;half(1,0,13,262,14'h1230);half(1,1,13,264,14'h1238);
  check(!event_valid,"dummy sprite excluded");obj_valid=1;
  half(0,0,7,6,14'h1230);half(0,1,7,8,14'h1238);check(!event_valid,"above crop excluded");
  half(0,0,231,254,14'h1230);half(0,1,231,256,14'h1238);check(!event_valid,"BG column33 excluded");
  seal(1);check(errors==0 && generation==1,"first set clean");
  for(i=0;i<8192;i++)ask(i,expected[i]);
  half(0,0,14,6,14'h1560);half(0,1,14,8,14'h1568);
  check(!event_valid,"owned set drops new events");
  for(i=0;i<8192;i++)ask(i,expected[i]);
  release_it();begin_it();seal(1);
  for(i=0;i<8192;i++)ask(i,0);
  // Low/high fetched across a committed mapper change cannot be represented
  // as one physical tile. Refuse it, rather than using a stale cached bank.
  release_it();begin_it();write_reg(16'h8000,8'h02);
  half(0,0,8,6,14'h1040);write_reg(16'h8001,99);half(0,1,8,8,14'h1048);
  check(!event_valid,"mixed physical bank planes refused");seal(0);check(errors==4,"plane mismatch cause");rejects++;
  ask(0,0);
  release_it();begin_it();ppu_valid=0;half(0,0,8,6,14'h1040);ppu_valid=1;
  half(0,1,8,8,14'h1048);seal(0);check(errors==6,"invalid sample and unmatched high");rejects++;
  release_it();begin_it();half(0,0,8,6,14'h1040);seal(0);
  check(errors==32,"unfinished pair at seal");rejects++;
  release_it();begin_it();extra_sprites=1;idle(2);extra_sprites=0;seal(0);
  check(errors==8,"unsupported extra sprite path explicit");rejects++;
  release_it();begin_it();rom_fault=1;idle(5);
  check(owned && !valid && errors==16,"fault with stopped PPU CE");rejects++;
  release_it();begin_it();half(0,0,8,6,14'h1040);release_it();
  begin_it();half(0,1,8,8,14'h1048);seal(0);check(errors==4,"release cancels incomplete pair");rejects++;
  release_it();begin_it();dut.generation=16'hffff;release_it();begin_it();seal(1);
  check(generation==0,"generation wraps without stale membership");
  // Controls for the displayed coordinate equations, independent of bitmap.
  for(i=0;i<8;i++)begin
   @(negedge clk);bg_ce=1;bg_clear=1;fine_x=i;@(negedge clk);bg_ce=0;bg_clear=0;
   for(j=321;j<=340;j++)bg_step(j,0);bg_step(0,0);
   for(j=1;j<=256;j++)bg_step(j,1);
  end
  for(i=0;i<2;i++)for(j=0;j<4;j++)begin
   @(negedge clk);spr_ce=1;spr_enabled=0;spr_size=i;spr_table=1;spr_range=1;
   @(negedge clk);spr_ce=0;
   for(k=0;k<5;k++)spr_step(k,8'h35,(j<<6)|8'h23);
   check(spr_valid && spr_attribute==((j<<6)|8'h23) && spr_x==237,"actual sprite metadata latches");
   check(spr_addr=={1'b1,7'h1a,(i?~j[1]:1'b1),1'b0,(3'd0^{3{j[1]}})},"actual 8x8/8x16 row and vertical flip");
   check(spr_load[3] && spr_load_data[26:19]==(j[0]?8'h96:8'h69),"actual horizontal flip low-plane consumption");
   spr_step(5,8'h35,(j<<6)|8'h23);spr_step(6,8'h35,(j<<6)|8'h23);
   check(spr_load[2] && spr_addr[3],"actual high-plane consumption phase");
   spr_step(7,8'h35,(j<<6)|8'h23);
  end
  @(negedge clk);spr_ce=1;spr_enabled=0;@(negedge clk);spr_ce=0;spr_range=0;
  spr_step(0,0,0);check(!spr_valid,"actual dummy evaluator flag");
  @(negedge clk);reset=1;query=1;@(posedge clk);#1;
  check(!owned && !response && !initialized,"reset cancels lease and starts scrub");
  $display("PASS FETCH165 checks=%0d events=%0d pixels=%0d rejects=%0d",checks,events,pixels,rejects);$finish;
 end
 initial begin #20000000;$fatal(1,"fetch165 watchdog");end
endmodule
