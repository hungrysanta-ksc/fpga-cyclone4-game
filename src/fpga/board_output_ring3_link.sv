// Source acknowledgements mean queued. Only committed_frame may release or
// publish the output page. Fence blocks the next frame until SRAM is drained.
module board_output_ring3_link(
 input wire source_clk,bus_clk,reset,frame_done,
 input wire lcd_on,source_pixel_valid,input wire[1:0]processing_bank,
 input wire pixel_valid,input wire[14:0]pixel_addr,input wire[15:0]pixel_data,output wire pixel_ready,
 input wire palette_valid,palette_initial,input wire[7:0]palette_after_row,
 input wire[5:0]palette_slot,input wire[14:0]palette_rgb,output wire palette_ready,
 input wire upload_start,bus_read_idle,output wire bus_busy,upload_done,bus_page,bus_front_valid,bus_error,
 output wire write_valid,input wire write_ready,output wire[15:0]write_addr,write_data,
 output wire write_word,committed_frame,
 output wire front_page,front_valid,published,source_error,host_upload_boundary,
 input wire discard,suspend,output wire state_drained
);
 wire display_visible;
 assign host_upload_boundary=boundary;
 assign state_drained=drained;
 wire word_valid,word_ready,byte_valid,byte_ready,boundary,read_idle,drained,page_error;
 wire pixel_ack,palette_ack;reg pending=0,fence_error=0;
 wire[15:0]word_addr,word_data,byte_addr;wire[7:0]byte_data;
 wire inhibit=pending||frame_done||suspend||discard;
 assign committed_frame=pending&&drained&&!reset&&!fence_error&&!suspend&&!discard;
 assign source_error=page_error||fence_error;
 assign pixel_ready=pixel_ack&&!inhibit;
 assign palette_ready=palette_ack&&!inhibit;
 always @(posedge source_clk)begin
  if(reset||discard)begin pending<=0;fence_error<=0;end
  else begin
   if(frame_done)begin pending<=1;if(pending)fence_error<=1;end
   else if(committed_frame)pending<=0;
  end
 end
 frame_output_pages pages(source_clk,reset,committed_frame,boundary,read_idle,
 pixel_valid&&!inhibit,pixel_addr,pixel_data,pixel_ack,
 palette_valid&&!inhibit,palette_initial,palette_after_row,palette_slot,palette_rgb,palette_ack,
 word_valid,word_ready,word_addr,word_data,byte_valid,byte_ready,byte_addr,byte_data,
 front_page,front_valid,published,page_error,discard,suspend);
 output_fifo_cdc writer(source_clk,bus_clk,reset,
 word_valid,word_addr,word_data,word_ready,byte_valid,byte_addr,byte_data,byte_ready,
 write_valid,write_ready,write_addr,write_data,write_word,drained);
 upload_boundary_cdc uploader(bus_clk,source_clk,reset,upload_start,bus_read_idle,
 bus_busy,upload_done,bus_page,bus_front_valid,bus_error,boundary,read_idle,front_page,display_visible&&!suspend);
 lcd_frame_visibility_ring3 visibility(source_clk,reset||discard,lcd_on,source_pixel_valid,
 palette_valid&&palette_ready&&palette_initial&&palette_slot==0,
 processing_bank,committed_frame,published,front_valid,display_visible);
endmodule
