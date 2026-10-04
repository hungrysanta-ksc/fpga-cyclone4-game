// Own an unused back page before preclearing its metadata. Output only:
// no changes to CPU/capture/planner/saves, and no additional frame buffers.
module frame_output_pages(
 input wire clk,reset,frame_done,upload_boundary,read_idle,
 input wire pixel_valid,input wire[14:0]pixel_addr,input wire[15:0]pixel_data,
 output wire pixel_ready,
 input wire palette_valid,palette_initial,input wire[7:0]palette_after_row,
 input wire[5:0]palette_slot,input wire[14:0]palette_rgb,output wire palette_ready,
 output wire word_valid,input wire word_ready,output wire[15:0]word_addr,word_data,
 output wire byte_valid,input wire byte_ready,output wire[15:0]byte_addr,output wire[7:0]byte_data,
 output wire front_page,front_valid,published,error,input wire discard,suspend
);
 wire can_start,back_page,pending,writing,page_error,meta_error;
 wire mv,mready;wire[14:0]ma;wire[15:0]md;
 // Do not begin on the publish edge itself: front/back changes on that edge.
 // No completion is synthesized. The unchanged source done/drain fence is
 // still required, so a precleared page alone can never become displayable.
 wire begin_frame=can_start&&!pending&&!frame_done&&!reset&&!discard&&!suspend;
 display_pages pages(clk,reset,begin_frame,frame_done,upload_boundary,read_idle,
 can_start,back_page,front_page,front_valid,pending,writing,published,page_error,discard);
 palette_hdma_word metadata(clk,reset||discard,frame_done,palette_valid,palette_initial,
 palette_after_row,palette_slot,palette_rgb,palette_ready,mv,mready,ma,md,meta_error,begin_frame);
 // output_fifo_cdc acknowledges enqueue one source clock later. Preserve
 // the selected owner across that interval, even if metadata becomes valid.
 reg owner_locked,owner_meta;
 wire select_meta=owner_locked?owner_meta:mv;
 always @(posedge clk)begin
  if(reset||discard||frame_done)begin owner_locked<=0;owner_meta<=0;end
  else if(owner_locked&&word_ready)owner_locked<=0;
  else if(!owner_locked&&writing&&(mv||pixel_valid)&&!error)begin
   owner_locked<=1;owner_meta<=mv;
  end
 end
 assign word_valid=(select_meta?mv:pixel_valid)&&writing&&!error&&!suspend&&!discard;
 assign pixel_ready=word_ready&&owner_locked&&!owner_meta&&writing&&!error&&!suspend&&!discard;
 assign word_addr={back_page,select_meta?ma:pixel_addr};assign word_data=select_meta?md:pixel_data;
 assign mready=word_ready&&owner_locked&&owner_meta&&writing&&!error&&!suspend&&!discard;
 assign byte_valid=0;assign byte_addr=0;assign byte_data=0;
 assign error=page_error||meta_error;
endmodule
