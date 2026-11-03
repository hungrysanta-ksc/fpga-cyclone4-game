// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module epoch573_tb;
 reg mem_clk=0,clk=0,nes_on=1,reset=0,run_enable=0,loaded=0,load_begin=0;
 reg load_valid=0,loader_fault=0,ppu_ce=0;
 always #2976 mem_clk=!mem_clk;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #23281 if(nes_on)clk=!clk;end
 wire nes_clk=clk;
 wire [18:0] loaded_bytes=loaded?19'h60000:0;
 wire request_reset,local_reset,memory_ready;
 nes_domain_reset124 init_release(clk,reset||!run_enable,request_reset);
 nes_local_memory local_memory(.clk(clk),.reset(request_reset),.init_done(memory_ready),
  .native_nt_address(11'd0),.cpumem_addr(25'd0),.cpumem_write(1'b0),.cpumem_dout(8'd0),
  .ppumem_addr(22'd0),.ppumem_write(1'b0),.ppumem_dout(8'd0),.external_cpu_data(8'd0),.external_ppu_data(8'd0));
 nes_domain_reset124 core_release(clk,reset||!run_enable||!memory_ready,local_reset);
 wire source_ready,source_is_rom,source_writing;wire [31:0] live_epoch;
 nes_source_epoch207 epoch(.*);
 wire [34:0] reference;
 epoch572 original(.source_ready(reference[34]),.source_is_rom(reference[33]),.source_writing(reference[32]),
                   .live_epoch(reference[31:0]),.*);
 wire capture_begin,initialized,lease_fault;
 wire [15:0] generation;
 nes_native_capture201 capture(.clk(clk),.reset(local_reset),.release_frame(1'b0),.ppu_ce(ppu_ce),
  .scanline(9'd7),.dot(9'd257),.rom_fault(1'b0),.source_ready(source_ready),.source_is_rom(source_is_rom),
  .source_writing(source_writing),.live_epoch(live_epoch),.export_error(4'd0),.reader_drained(1'b1),
  .retire_commit(1'b0),.retire_generation(16'd0),.query(1'b0),.display_mask(8'd0),
  .bg_low(1'b0),.bg_high(1'b0),.obj_low(1'b0),.obj_high(1'b0),.obj_valid(1'b0),.extra_sprites(1'b0),
  .ppu_read(1'b0),.ppu_valid(1'b0),.scroll_access(1'b0),.color(6'd0),.emphasis(3'd0),
  .bg_attribute(2'd0),.obj_attribute(8'd0),.obj_x(8'd0),.logical_address(14'd0),.physical_address(22'd0),
  .scroll_v(15'd0),.scroll_t(15'd0),.fine_x(3'd0),.pattern_mode(3'd0),.palette(192'd0),
  .query_kind(3'd0),.query_index(13'd0),.query_generation(16'd0),
  .capture_begin(capture_begin),.initialized(initialized),.lease_fault(lease_fault),.generation(generation));
 integer tick=0,checks=0;bit armed=0;
 always @(posedge clk)tick++;
 always @(posedge clk or negedge clk or posedge mem_clk or posedge local_reset)begin
  #2;if(armed)begin
   if(reference!=={source_ready,source_is_rom,source_writing,live_epoch})
    $fatal(1,"epoch visibility reset=%b ready=%b ref=%h actual=%h",local_reset,source_ready,reference[31:0],live_epoch);
   checks++;
  end
 end
 task publish;
  @(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
 endtask
 task first_generation(input integer pass,input reg [31:0] want);
  integer start_at,core_at,ready_at,init_at;
  @(negedge clk);#3;run_enable=1;start_at=tick;
  @(negedge local_reset);core_at=tick;
  @(posedge source_ready);ready_at=tick;
  if(live_epoch!==want||reference[31:0]!==want)$fatal(1,"ready epoch");
  @(posedge initialized);init_at=tick;
  // Supply the first eligible PPU event immediately after the real collector scrub.
  @(negedge clk);ppu_ce=1;#2;if(!capture_begin||generation!==0)$fatal(1,"first capture");
  @(posedge clk);#3;ppu_ce=0;
  if(lease_fault||generation!==1||!capture.ownership.capturing||
     capture.ownership.capture_generation!==1||capture.ownership.capture_epoch!==want)$fatal(1,"generation ownership");
  $display("FIRST573 %0d %08h %0d %0d %0d %0d",pass,want,core_at-start_at,ready_at-start_at,init_at-start_at,tick-start_at);
 endtask
 initial begin
  #100;reset=1;#100;armed=1;
  repeat(3)@(negedge mem_clk);reset=0;
  // Accelerate only the serial counter, then change bit 23 through real BEGIN.
  epoch.serial=32'h007fffff;original.serial=32'h007fffff;
  publish();loaded=1;first_generation(0,32'h00c00000);
  @(negedge clk);nes_on=0;run_enable=0;#10;
  if(source_ready||live_epoch!==0||!local_reset)$fatal(1,"STOP with no NES edge");
  repeat(12)@(negedge mem_clk);nes_on=1;first_generation(1,32'h00c00000);
  @(negedge clk);nes_on=0;run_enable=0;loaded=0;publish();publish();
  repeat(8)@(negedge mem_clk);loaded=1;
  if(source_ready||live_epoch!==0)$fatal(1,"reload with no NES edge");
  nes_on=1;first_generation(2,32'h00c00003);
  @(negedge clk);run_enable=0;loaded=0;nes_on=0;
  @(negedge mem_clk);epoch.serial=32'hffffffff;original.serial=32'hffffffff;
  publish();loaded=1;run_enable=1;nes_on=1;
  @(negedge local_reset);repeat(12)@(negedge clk);
  if(!epoch.exhausted||source_ready||lease_fault)$fatal(1,"wrapped epoch admitted");
  $display("PASS573 comparisons=%0d",checks);$finish;
 end
 initial begin #(64'd4000000000);$fatal(1,"timeout");end
endmodule
