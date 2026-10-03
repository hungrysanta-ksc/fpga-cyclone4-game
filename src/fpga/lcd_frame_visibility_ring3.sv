// A committed page is displayable only if its complete source frame belongs
// to the current LCD-on interval. Keep ownership of old pages, but report them
// as not displayable until a fresh frame has actually been published.
// The SNES frontend must render its white GB viewport when visible is false.
module lcd_frame_visibility_ring3(
 input wire clk,reset,lcd_on,source_pixel_valid,
 input wire palette_begin,input wire[1:0]processing_bank,input wire committed_frame,published,front_valid,
 output wire visible
);
 reg[14:0]position;
 reg[1:0]source_bank;
 reg[2:0]bank_fresh;
 reg active_fresh,pending_fresh,front_fresh;
 assign visible=lcd_on&&front_valid&&front_fresh&&!reset;
 always @(posedge clk)begin
  if(reset)begin
   position<=0;source_bank<=0;bank_fresh<=0;
   active_fresh<=0;pending_fresh<=0;front_fresh<=0;
  end else if(!lcd_on)begin
   position<=0;bank_fresh<=0;active_fresh<=0;pending_fresh<=0;front_fresh<=0;
   // Abandoned partial frames do not advance the capture bank.
  end else begin
   if(source_pixel_valid)begin
    if(position==23039)begin
     bank_fresh[source_bank]<=1;source_bank<=source_bank==2?2'd0:source_bank+1'b1;position<=0;
    end else position<=position+1'b1;
   end
   if(palette_begin)active_fresh<=bank_fresh[processing_bank];
   if(committed_frame)pending_fresh<=active_fresh;
   if(published)front_fresh<=committed_frame?active_fresh:pending_fresh;
  end
 end
endmodule
