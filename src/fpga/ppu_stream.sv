// MiSTer video.v updates LCD outputs on ce; consume once on the NEXT edge.
// lcd_clkena itself is a held level, not a system-clock pulse.
module ppu_stream(input wire clk,reset,ppu_ce,lcd_on,lcd_clkena,
 input wire[14:0]lcd_data,output wire pixel_valid,output wire[14:0]pixel_rgb);
 reg tick;
 always @(posedge clk)if(reset)tick<=0;else tick<=ppu_ce;
 assign pixel_valid=!reset&&tick&&lcd_on&&lcd_clkena;
 assign pixel_rgb=lcd_data;
endmodule
