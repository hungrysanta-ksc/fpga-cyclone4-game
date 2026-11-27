// Compare runtime writes, mirroring and rendering-edge copies against the original PPU.
`timescale 1ns/1ps
module ff3_palette1039_tb;
 reg clk=0;
 always #5 clk=!clk;
 reg ce=1, reset=1, write=0, rendering=0, c_corrupt=0, in_range=0;
 reg [4:0] addr=0, raw_addr=0;
 reg [5:0] din=0;
 wire [191:0] native_actual,native_reference;
 wire [95:0] tap_actual,tap_reference;
 wire [5:0] actual_color,reference_color;
 wire [1:0] extra_bits=0;
 wire [63:0] SaveStateBus_Din=0;
 wire [9:0] SaveStateBus_Adr=0;
 wire SaveStateBus_wren=0, SaveStateBus_rst=reset;
 PaletteRam actual(.palette_access(1'b0),.palette_data(6'd0),.palette_address(5'd0),
   .palette_read(),.SaveStateBus_load(1'b0),.dout(actual_color),.native_palette(native_actual),
   .tap_palette(tap_actual),.SaveStateBus_Dout(),.*);
 PaletteRam_reference original(.dout(reference_color),.native_palette(native_reference),
   .tap_palette(tap_reference),.SaveStateBus_Dout(),.*);
 task automatic compare_edge;
   @(posedge clk);#1;
   if({actual_color,native_actual,tap_actual}!=={reference_color,native_reference,tap_reference})
     $fatal(1,"palette output addr=%0d raw=%0d write=%b",addr,raw_addr,write);
   for(int i=0;i<32;i++) if(actual.palette[i]!==original.palette[i])
     $fatal(1,"raw palette %0d differs at addr=%0d raw=%0d",i,addr,raw_addr);
 endtask
 initial begin
   repeat(3) @(negedge clk);
   reset=0;
   // Each raw/address pair sees a rendering falling edge, both with and
   // without a simultaneous CPU write. They may target distinct entries.
   for(int w=0; w<2; w++) for(int a=0;a<32;a++) for(int r=0;r<32;r++) begin
     @(negedge clk);rendering=1;addr=a;raw_addr=r;din=r+3*a;write=1;ce=1;
     compare_edge();
     @(negedge clk);rendering=0;write=w;c_corrupt=1;in_range=1;din=~din;
     compare_edge();
     @(negedge clk);ce=0;din=din+1;compare_edge();
   end
   $display("PASS FF3 palette 2048 rendering transitions, mirrored reads, concurrent writes and CE stalls");
   $finish;
 end
endmodule
