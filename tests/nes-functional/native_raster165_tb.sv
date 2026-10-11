// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_raster165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ppu_ce=0,scroll_access=0,source_fault=0,release_packet=0;
 reg query=0,query_palette=0;reg [7:0] query_row=0;
 reg [4:0] query_bank=0,query_color=0;
 reg [8:0] scanline=0,dot=0;
 reg [14:0] scroll_v=0,scroll_t=0;reg [2:0] fine_x=0,pattern_mode=0;
 reg [7:0] display_mask=8'h1e;reg [191:0] palette=0;
 wire owned,valid,response,hit;wire [15:0] generation;
 wire [7:0] errors,row_count;wire [5:0] palette_count;wire [55:0] data;
 nes_native_raster165 dut(.*);
 integer checks=0,frames=0,rejections=0,i,j,k;
 reg [55:0] expected[0:223];reg [191:0] expected_pal[0:31];
 function automatic [191:0] colors_for(input integer bank);
  integer c;begin for(c=0;c<32;c=c+1)colors_for[c*6+:6]=(c*3+bank)&63;end
 endfunction
 task check(input bit ok,input string name);
  begin checks=checks+1;if(!ok)$fatal(1,"raster165 %s",name);end
 endtask
 task step(input integer line,input integer x);
  begin @(negedge clk);scanline=line;dot=x;ppu_ce=1;@(posedge clk);#1;
   @(negedge clk);ppu_ce=0;end
 endtask
 task idle(input integer clocks);
  begin repeat(clocks)@(negedge clk);end
 endtask
 task release_it;
  begin @(negedge clk);release_packet=1;query=1;@(posedge clk);#1;
   check(!owned && !valid && !response,"release cancels query/lease");
   @(negedge clk);release_packet=0;query=0;end
 endtask
 task ask(input bit pal,input integer row,input integer bank,input integer color,input bit good,input [55:0] want);
  begin @(negedge clk);query=1;query_palette=pal;query_row=row;query_bank=bank;query_color=color;
   @(posedge clk);#1;check(response && hit==good && data===want,"immutable packet query");
   @(negedge clk);query=0;end
 endtask
 // Every row has different raw scroll state. Palette changes only at boundaries.
 // Synthetic PPU timing deliberately shortens blank portions; no core gameplay.
 task frame(input integer variant);
  integer r,b;begin
   for(r=0;r<224;r=r+1)begin
    b=(variant==7)?0:(variant==1 && r<33)?r:((variant==1)?32:r/7);
    palette=colors_for(b);scroll_v=(r*31)&32767;scroll_t=(r*79)&32767;
    fine_x=r%8;pattern_mode=r%8;display_mask=(r%2)?8'h1e:8'hfe;
    if(b<32)expected_pal[b]=palette;
    expected[r]={7'd0,b[4:0],display_mask,pattern_mode,fine_x,scroll_t,scroll_v};
    if(!(variant==2 && r==80))step(r+8,1);
    idle(35);
    if(variant==3 && r==80)palette[0]=~palette[0];
    if(variant==4 && r==80)scroll_access=1;
    if(variant==5 && r==80)source_fault=1;
    step(r+8,128);
    if(variant==5 && r==80)check(owned && !valid,"fault retires before end of frame");
    scroll_access=0;source_fault=0;
    step(r+8,256);
   end
   if(variant==6)source_fault=1;
   step(232,1);source_fault=0;frames=frames+1;
   check(owned,"frame sealed");
   if(variant==0 || variant==7)check(valid && errors==0 && row_count==224 && palette_count==((variant==7)?1:32),"palette boundary exact capacity");
   else begin
    check(!valid && errors!=0,"bad frame withheld");
    case(variant)
     1:check(errors==8'h04,"palette capacity cause");
     // Missing a row with different x/mode also changes state within the old row.
     2:check(errors==8'h09,"row gap and changed horizontal state causes");
     3:check(errors==8'h08,"horizontal palette cause");
     4:check(errors==8'h10,"horizontal CPU access cause");
     5,6:check(errors==8'h20,"source fault cause including seal edge");
    endcase
    rejections=rejections+1;
   end
  end
 endtask
 // Execute the actual upstream PaletteRam, including aliases and corruption.
 reg pal_reset=1,pal_ce=1,pal_write=0,rendering=0,c_corrupt=0;
 reg [4:0] pal_addr=0,raw_addr=0;reg [5:0] pal_din=0;
 wire [5:0] pal_dout;wire [191:0] native_palette;wire [95:0] tap_palette;
 PaletteRam actual_palette(.clk(clk),.reset(pal_reset),.ce(pal_ce),.addr(pal_addr),
  .din(pal_din),.dout(pal_dout),.write(pal_write),.extra_bits(2'b00),
  .rendering(rendering),.c_corrupt(c_corrupt),.raw_addr(raw_addr),.in_range(1'b1),
  .SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),
  .SaveStateBus_rst(1'b1),.SaveStateBus_Dout(),.tap_palette(tap_palette),.native_palette(native_palette));
 task pal_put(input integer address,input integer value);
  begin @(negedge clk);pal_write=1;pal_addr=address;pal_din=value;
   @(negedge clk);pal_write=0;end
 endtask
 // Seeded actual PPU observation boundaries, not a second game boot.
 wire [1:0] sys_type=2'b00;
 wire [14:0] native_scroll_v,native_scroll_t;wire [2:0] native_fine_x,native_pattern_mode;
 wire [7:0] native_display_mask;wire [191:0] ppu_palette;wire native_scroll_access;
 PPU actual_ppu(.clk(clk),.ce(1'b0),.reset(1'b0),.cold_reset(1'b0),.cs(1'b0),.RWn(1'b1),
  .rst_behavior(1'b0),.debug_dots(1'b0),.sys_type(sys_type),.vs_ppu_type(4'd0),
  .din(8'd0),.ain(3'd0),.read(1'b0),.write(1'b0),.vram_dbus_in(8'd0),
  .extra_sprites(1'b0),.mask(2'b00),.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),
  .SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b1),.SaveStateBus_load(1'b0),
  .Savestate_OAMAddr(8'd0),.Savestate_OAMRdEn(1'b0),.Savestate_OAMWrEn(1'b0),.Savestate_OAMWriteData(8'd0),
  .native_scroll_v(native_scroll_v),.native_scroll_t(native_scroll_t),.native_fine_x(native_fine_x),
  .native_pattern_mode(native_pattern_mode),.native_display_mask(native_display_mask),
  .native_palette(ppu_palette),.native_scroll_access(native_scroll_access));
 initial begin
  idle(4);reset=0;pal_reset=0;
  for(i=0;i<32;i=i+1)pal_put(i,i+7);
  for(i=0;i<32;i=i+1)begin
   j=(i%4==0)?(i&15):i;k=(j%4==0)?j+23:j+7;
   check(native_palette[i*6+:6]===k[5:0],"actual palette logical alias/OBJ export");
  end
  pal_put(1,6'h2a);pal_put(3,6'h07);
  @(negedge clk);rendering=1;pal_addr=1;raw_addr=3;c_corrupt=1;
  @(negedge clk);rendering=0;@(negedge clk);c_corrupt=0;
  check(native_palette[18+:6]===6'h2a,"actual palette corruption visible");
  // Delayed $2006 and $2007 effects must not disappear between CPU accesses.
  actual_ppu.vram0.vram_v=15'h2345;actual_ppu.vram0.vram_t=15'h5678;actual_ppu.vram0.vram_x=3'd6;
  actual_ppu.vram0.write_shift=0;actual_ppu.read_2007_delayed=0;actual_ppu.write_2007_delayed=0;
  actual_ppu.obj_size1=1;actual_ppu.bg_patt1=0;actual_ppu.obj_patt1=1;
  actual_ppu.emph_reg=3'b101;actual_ppu.enable_objects=1;actual_ppu.enable_playfield=1;
  actual_ppu.object_clip=0;actual_ppu.playfield_clip=1;actual_ppu.grayscale=0;
  #1;check(native_scroll_v===15'h2345 && native_scroll_t===15'h5678 && native_fine_x===6 &&
   native_pattern_mode===5 && native_display_mask===8'hba && !native_scroll_access,"actual PPU raw state export");
  actual_ppu.vram0.write_shift=2;#1;check(native_scroll_access,"delayed 2006 export");
  actual_ppu.vram0.write_shift=0;actual_ppu.read_2007_delayed=16;#1;check(native_scroll_access,"delayed 2007 export");
  actual_ppu.read_2007_delayed=0;
  @(negedge clk);query=1;@(posedge clk);#1;check(!response && !hit,"unowned query withheld");
  @(negedge clk);query=0;scanline=8;dot=1;idle(4);check(!dut.active,"CE low ignores line marker");
  frame(0);
  // Core/source changing during a lease cannot rewrite the packet.
  palette=~palette;scroll_v=0;step(8,1);check(generation==1,"lease skips next frame");
  for(i=0;i<224;i=i+1)ask(0,i,0,0,1,expected[i]);
  for(i=0;i<32;i=i+1)for(j=0;j<32;j=j+1)ask(1,0,i,j,1,{50'd0,expected_pal[i][j*6+:6]});
  ask(0,224,0,0,0,0);release_it();
  for(k=1;k<=6;k=k+1)begin
   frame(k);ask(0,0,0,0,0,0);release_it();
  end
  // A new frame overwrites all published rows; old invalid generations cannot leak.
  frame(0);check(generation==8,"generation counter");ask(0,223,0,0,1,expected[223]);
  release_it();frame(7);ask(1,0,1,0,0,0);ask(1,0,0,31,1,{50'd0,expected_pal[0][186+:6]});
  @(negedge clk);reset=1;query=1;@(posedge clk);#1;
  check(!owned && !valid && !response && generation==0,"reset cancels query/lease");
  @(negedge clk);reset=0;query=0;
  // Back-to-back artificial palette row requests outrun 32-clock serialization.
  palette=colors_for(0);step(8,1);palette=colors_for(1);step(9,1);idle(40);step(232,1);
  check(owned && !valid && errors[1],"palette copy overrun rejects frame");rejections=rejections+1;release_it();
  palette=colors_for(0);step(8,1);source_fault=1;idle(2);
  check(owned && !valid && errors[5] && !dut.copy_busy,"fault retires with PPU CE stopped");
  source_fault=0;rejections=rejections+1;release_it();
  $display("PASS RASTER165 checks=%0d frames=%0d rejections=%0d",checks,frames,rejections);$finish;
 end
 initial begin #5000000;$fatal(1,"watchdog");end
endmodule
