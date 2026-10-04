// Ownership only: all inputs must already be in clk's domain. Boundary means
// SNES explicitly starts a fresh upload, NOT an arbitrary observed scanline.
// The producer must wait for writer_ready before beginning output writes.
module display_pages(
 input wire clk,reset,writer_begin,writer_done,upload_boundary,read_idle,
 output wire writer_ready,output wire write_page,
 output reg front_page,front_valid,frame_pending,writing,
 output wire published,output reg error,input wire discard
);
 assign published=upload_boundary&&read_idle&&(frame_pending||(writer_done&&writing))&&!error&&!discard;
 assign writer_ready=!writing&&(!frame_pending||published)&&!error&&!discard;
 assign write_page=!front_page;
 always @(posedge clk)begin
  if(reset)begin front_page<=0;front_valid<=0;frame_pending<=0;writing<=0;error<=0;end
  else if(discard)begin frame_pending<=0;writing<=0;error<=0;end
  else if(!error)begin
   if(writer_begin)begin
    if(!writer_ready)error<=1;else writing<=1;
   end
   if(writer_done)begin
    if(!writing)error<=1;
    else begin writing<=0;frame_pending<=1;end
   end
   if(published)begin front_page<=!front_page;front_valid<=1;frame_pending<=0;end
  end
 end
endmodule
