// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module ncr1_tap_tb;
reg queue_clk=0;always #5 queue_clk=~queue_clk;
reg reset=1,arm=1,immutable_chr=1,chr_32k=1,tap_ce=0,tap_bgp=1,tap_mode=1;
reg [8:0] cycle=0,scanline=511;reg [2:0] tap_fine=0;reg [14:0] tap_scroll=0;
reg [95:0] tap_palette=96'h5b084f5b084f5b084f5b084f;reg [1:0] tap_attribute=0;
reg tap_ppu_change=0,tap_mapper_change=0,ppumem_read=1,ppumem_write=0;
reg [21:0] ppumem_addr=22'h200000;
wire frame_start,frame_end,supported_mode,bg_valid,tap_fault;wire [7:0] frame_id,tap_error;
wire [2:0] fine_x;wire [63:0] palette_snes;wire signed [8:0] bg_line;
wire [8:0] bg_dot;wire [14:0] bg_chr_address;wire [1:0] bg_palette;wire [31:0] bg_tick;
integer checks=0;
nes_ncr1_ppu_tap tap(.*);
task automatic defaults;
 @(negedge queue_clk);reset=1;arm=1;immutable_chr=1;chr_32k=1;tap_ce=0;tap_bgp=1;tap_mode=1;cycle=0;scanline=511;tap_fine=0;tap_scroll=0;tap_palette=96'h5b084f5b084f5b084f5b084f;tap_attribute=0;tap_ppu_change=0;tap_mapper_change=0;ppumem_read=1;ppumem_write=0;ppumem_addr=22'h200000;
 repeat(2)@(negedge queue_clk);reset=0;
endtask
task automatic start;
 tap_ce=1;cycle=1;#1;if(!frame_start || !supported_mode)$fatal(1,"start");
 @(negedge queue_clk);tap_ce=0;cycle=2;
endtask
task automatic fail(input integer code,input string name);
 repeat(2)@(negedge queue_clk);
 if(!tap_fault || tap_error!=code || supported_mode || bg_valid || frame_start || frame_end)$fatal(1,"missing fail closed %s",name);
 checks++;$display("PASS TAP %s",name);
endtask
initial begin
 defaults();start();
 for(integer i=0;i<4;i++)begin
  tap_ce=1;cycle=6;tap_attribute=i;#1;
  if(!bg_valid || bg_dot!=5 || bg_line!=-1 || bg_palette!=0 || bg_chr_address!=0)$fatal(1,"attribute equivalence");
  @(negedge queue_clk);tap_ce=0;
 end
 checks++;$display("PASS TAP equivalent_real_attribute_groups");
 tap_ce=1;cycle=262;tap_bgp=0;#1;if(bg_valid)$fatal(1,"sprite classified as BG");checks++;
 tap_ce=0;tap_bgp=1;cycle=6;#1;if(bg_valid)$fatal(1,"clock enable");checks++;
 tap_ce=1;scanline=241;#1;if(bg_valid)$fatal(1,"vblank classified as BG");checks++;
 scanline=240;cycle=1;#1;if(!frame_end)$fatal(1,"end");@(negedge queue_clk);tap_ce=0;
 if(frame_id!=2)$fatal(1,"frame sequence");checks++;
 tap_mapper_change=1;tap_ppu_change=1;repeat(2)@(negedge queue_clk);if(tap_fault)$fatal(1,"vblank changes forbidden");checks++;
 defaults();start();tap_mode=0;fail(1,"sprite_mask_or_color_mode");
 defaults();start();tap_palette[6]=!tap_palette[6];fail(1,"palette_divergence");
 defaults();start();tap_scroll=1;fail(1,"coarse_vertical_scroll");
 defaults();start();immutable_chr=0;fail(1,"mutable_CHR");
 defaults();start();tap_fine=1;fail(2,"fineX_change");
 defaults();start();tap_mapper_change=1;fail(2,"mapper_change");
 defaults();start();tap_ce=1;tap_ppu_change=1;fail(2,"PPU_change");
 defaults();start();ppumem_write=1;fail(2,"CHR_write");
 defaults();start();tap_ce=1;cycle=6;ppumem_addr=22'h208000;fail(3,"physical_CHR_range");
 defaults();chr_32k=0;start();tap_ce=1;cycle=6;ppumem_addr=22'h204000;fail(3,"16KiB_range");
 defaults();start();tap_ce=1;cycle=6;ppumem_read=0;fail(3,"missing_memory_read");
 defaults();tap_palette=0;tap_ce=1;cycle=1;fail(1,"unsupported_start");
 defaults();start();tap_ce=1;cycle=6;ppumem_addr=22'h204000;#1;if(!bg_valid || bg_chr_address!=15'h4000 || !supported_mode)$fatal(1,"32KiB address bit lost");checks++;
 defaults();#1;if(tap_fault || frame_id!=1)$fatal(1,"reset recovery");checks++;
 $display("PASS TAP CHECKS=%0d",checks);$finish;
end
initial begin #100000;$fatal(1,"watchdog");end
endmodule
