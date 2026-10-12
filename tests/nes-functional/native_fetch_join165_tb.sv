// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Runs the EXACT generated collector/scene binding, not the full board/core.
module native_fetch_join165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,tap_ce=0,rom_fault=0,native_release_scene=0,native_memory_query=0;
 reg [8:0] scanline=0,cycle=0;
 wire native_scene_owned,native_snapshot_valid,native_required_owned,native_required_valid;
 wire [15:0] native_generation;
 wire [7:0] native_fetch_errors,native_memory_data;
 wire native_memory_response,native_memory_hit;
 fetch_join_harness h(.clk(clk),.reset(reset),.tap_ce(tap_ce),.rom_fault(rom_fault),
  .ppumem_read(1'b0),.rom_ppu_valid(1'b0),.native_chr_logical(14'd0),.ppumem_addr(22'd0),.ppumem_din(8'd0),
  .scanline(scanline),.cycle(cycle),.tap_attribute(2'd0),
  .native_bg_low(1'b0),.native_bg_high(1'b0),.native_obj_low(1'b0),.native_obj_high(1'b0),
  .native_obj_valid(1'b0),.native_obj_attribute(8'd0),.native_obj_x(8'd0),.native_extra_sprites(1'b0),
  .native_scroll_v(15'd0),.native_scroll_t(15'd0),.native_fine_x(3'd0),.native_pattern_mode(3'd0),
  .native_display_mask(8'd0),.native_palette(192'd0),.native_scroll_access(1'b0),
  .native_nt_data(8'd0),.native_oam_data(8'd0),.native_nt_write(1'b0),.native_oam_write(1'b0),
  .native_release_scene(native_release_scene),.native_query(1'b0),.native_state_query(1'b0),
  .native_required_query(1'b0),.native_memory_query(native_memory_query),.native_memory_address(12'd2048),
  .native_scene_owned(native_scene_owned),.native_snapshot_valid(native_snapshot_valid),
  .native_required_owned(native_required_owned),.native_required_valid(native_required_valid),
  .native_generation(native_generation),.native_fetch_errors(native_fetch_errors),
  .native_memory_response(native_memory_response),.native_memory_hit(native_memory_hit),.native_memory_data(native_memory_data));
 integer checks=0,i;
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"join165 %s",why);end endtask
 task idle(input integer n);begin repeat(n)@(negedge clk);end endtask
 task step(input integer y,input integer x);
  begin @(negedge clk);scanline=y;cycle=x;tap_ce=1;@(negedge clk);tap_ce=0;end
 endtask
 task release_it;
  begin @(negedge clk);native_release_scene=1;native_memory_query=1;
   @(posedge clk);#1;check(!native_scene_owned && !native_memory_response,"common release cancels query");
   @(negedge clk);native_release_scene=0;native_memory_query=0;rom_fault=0;
   idle(8194);
  end
 endtask
 initial begin
  idle(3);reset=0;idle(8194);
  step(8,1);check(!h.native_scene.active && !h.native_scene.raster.active,"missing prefetch start cannot create mismatched scene");
  step(7,257);check(h.native_required_active,"early capture armed");
  rom_fault=1;idle(6);
  check(native_scene_owned && !native_snapshot_valid && native_fetch_errors==16 && native_generation==1,
   "before-row8 fault retires common lease without PPU CE");
  native_memory_query=1;idle(2);check(!native_memory_response && !native_memory_hit,"invalid scene cannot query stale memory");
  release_it();step(8,1);check(!h.native_scene.active,"release also requires next prefetch boundary");
  step(7,257);
  for(i=8;i<232;i++)begin step(i,1);idle(35);end
  step(232,1);idle(10);
  check(native_scene_owned && native_snapshot_valid && native_required_valid && native_generation==2,
   "matching successful set joins state/cache/copy drain");
  native_memory_query=1;idle(2);
  check(native_memory_response && native_memory_hit && native_memory_data==0,"joined memory query");
  release_it();step(7,257);step(8,1);idle(10);rom_fault=1;idle(10);
  check(native_scene_owned && !native_snapshot_valid && native_fetch_errors==16,"in-copy fault joins stopped CE");
  release_it();step(7,257);step(8,1);idle(10);release_it();
  check(!native_scene_owned && !h.native_scene.active && !h.native_required_active,"release during copy cancels both captures");
  $display("PASS FETCHJOIN165 checks=%0d",checks);$finish;
 end
 initial begin #5000000;$fatal(1,"join165 watchdog");end
endmodule
