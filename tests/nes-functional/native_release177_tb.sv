// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Full341-dot/262-line cadence; synthetic legal BG, no CPU/PSRAM/fill/host.
module native_release177_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_frame=0;integer tick=0;
 always @(negedge clk)if(reset)tick=0;else tick=tick+1;
 wire ppu_ce=tick%4==0;
 wire [8:0] scanline=(tick/4/341)%262,dot=(tick/4)%341;
 wire pre=dot==326||dot==328||dot==334||dot==336;
 wire visible=scanline>=8&&scanline<232;
 wire low_event=(visible&&dot>=6&&dot<=246&&(dot-6)%8==0)||((scanline>=7&&scanline<231)&&(dot==326||dot==334));
 wire high_event=(visible&&dot>=8&&dot<=248&&dot%8==0)||((scanline>=7&&scanline<231)&&(dot==328||dot==336));
 wire [12:0] column=pre?(dot>=334?1:0):((dot+7)/8)+1;
 wire [2:0] fine=(pre?scanline+1:scanline)&7;
 wire [13:0] logical_address=column*16+(high_event?8:0)+fine;
 wire owned,geometry_valid,initialized,active,response,hit,scroll_seen;
 wire [15:0] generation;wire [24:0] errors;wire [63:0] data;
 wire [7:0] row_count,object_count,exception_count;wire [5:0] group_count,palette_count;
 nes_native_frame165 dut(.clk(clk),.reset(reset),.release_frame(release_frame),.ppu_ce(ppu_ce),.rom_fault(1'b0),
  .scanline(scanline),.dot(dot),.bg_low(low_event),.bg_high(high_event),.obj_low(1'b0),.obj_high(1'b0),.obj_valid(1'b0),.extra_sprites(1'b0),
  .bg_attribute(2'd0),.obj_attribute(8'd0),.obj_x(8'd0),.ppu_read(low_event||high_event),.ppu_valid(low_event||high_event),
  .logical_address(logical_address),.physical_address(22'h200000+logical_address),.scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),.pattern_mode(3'd0),
  .display_mask(8'h1e),.palette(192'd0),.scroll_access(1'b0),.query(1'b0),.query_kind(3'd0),.query_index(13'd0),.query_generation(16'd0),
  .owned(owned),.geometry_valid(geometry_valid),.initialized(initialized),.active(active),.generation(generation),.errors(errors),.scroll_seen(scroll_seen),
  .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),
  .response(response),.hit(hit),.data(data));
 integer phase[0:13];integer i,j,start_tick,checks=0;reg [15:0] prior_gen;
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"case%0d phase%0d %s gen=%0d err=%h",i,phase[i],why,generation,errors);end endtask
 initial begin
  phase[0]=0;phase[1]=1;phase[2]=8191;phase[3]=8192;
  phase[4]=(7*341+257)*4-1;phase[5]=(7*341+257)*4;phase[6]=(7*341+257)*4+1;
  phase[7]=(8*341+1)*4-1;phase[8]=(8*341+1)*4;phase[9]=(8*341+1)*4+1;
  phase[10]=(232*341+1)*4-1;phase[11]=(232*341+1)*4;phase[12]=(232*341+1)*4+1;phase[13]=357367;
  repeat(5)@(posedge clk);#1;reset=0;
  for(i=0;i<14;i=i+1)begin
   wait(owned);@(posedge clk);#1;
   check(geometry_valid&&errors==0&&row_count==224,"first/reused candidate valid");prior_gen=generation;
   // A real consumer can release at any NES-clock phase, not just frame start.
   wait(tick%357368==phase[i]);release_frame=1;
   @(posedge clk);#1;release_frame=0;check(!owned&&!active&&!initialized,"shared release clears ownership and starts scrub");
   start_tick=tick;
   while(!owned&&tick-start_tick<714736)begin @(posedge clk);#1;end
   check(owned&&geometry_valid&&errors==0&&generation==prior_gen+1,"next legal frame within two frame periods");
   $display("RELEASE177 case=%0d phase=%0d wait_ticks=%0d generation=%0d",i,phase[i],tick-start_tick,generation);
  end
  $display("PASS RELEASE177 cases=14 checks=%0d",checks);$finish;
 end
 initial begin #180000000;$fatal(1,"release watchdog");end
endmodule
