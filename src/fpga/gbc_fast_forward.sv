// One captured frame at normal speed, then eight discarded accelerated frames.
// Phase changes only at line-0 VSYNC, before visible pixels. R release finishes
// a discarded frame; restore clears phase together with the capture engine.
module gbc_fast_forward(input wire clk,reset,requested,lcd_on,lcd_vsync,
 output wire speedup,keep_pixels,output reg active);
 reg previous_vsync;reg[3:0]phase;
 always @(posedge clk)begin
  if(reset)begin previous_vsync<=0;phase<=0;active<=0;end
  else begin
   previous_vsync<=lcd_vsync;
   if(!lcd_on)begin phase<=0;active<=0;end
   else if(lcd_vsync&&!previous_vsync)begin
    active<=requested;
    if(!requested)phase<=0;else phase<=phase==8?0:phase+1'b1;
   end
  end
 end
 assign speedup=phase!=0;assign keep_pixels=phase==0;
endmodule
