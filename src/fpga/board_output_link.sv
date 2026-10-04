// Video-to-board boundary. SRAM pin arbitration and SNES register decoding
// remain external. bus_busy requires the adapter to inhibit new frame reads.
module board_output_link(
 input wire source_clk,bus_clk,reset,frame_done,
 input wire pixel_valid,input wire[14:0]pixel_addr,input wire[15:0]pixel_data,output wire pixel_ready,
 input wire palette_valid,palette_initial,input wire[7:0]palette_after_row,
 input wire[5:0]palette_slot,input wire[14:0]palette_rgb,output wire palette_ready,
 input wire upload_start,bus_read_idle,output wire bus_busy,upload_done,bus_page,bus_front_valid,bus_error,
 output wire write_valid,input wire write_ready,output wire[15:0]write_addr,output wire[7:0]write_data,
 output wire front_page,front_valid,published,source_error
);
 wire word_valid,word_ready,byte_valid,byte_ready,boundary,read_idle;
 wire[15:0]word_addr,word_data,byte_addr;wire[7:0]byte_data;
 frame_output_pages pages(source_clk,reset,frame_done,boundary,read_idle,
 pixel_valid,pixel_addr,pixel_data,pixel_ready,
 palette_valid,palette_initial,palette_after_row,palette_slot,palette_rgb,palette_ready,
 word_valid,word_ready,word_addr,word_data,byte_valid,byte_ready,byte_addr,byte_data,
 front_page,front_valid,published,source_error,1'b0,1'b0);
 output_write_cdc writer(source_clk,bus_clk,reset,
 word_valid,word_addr,word_data,word_ready,byte_valid,byte_addr,byte_data,byte_ready,
 write_valid,write_ready,write_addr,write_data);
 upload_boundary_cdc uploader(bus_clk,source_clk,reset,upload_start,bus_read_idle,
 bus_busy,upload_done,bus_page,bus_front_valid,bus_error,boundary,read_idle,front_page,front_valid);
endmodule
