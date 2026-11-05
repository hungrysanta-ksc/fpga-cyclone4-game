// Selected export/mailbox/SPI topology; query values are the sealed capture fixture.
 wire busy,send,can_send,valid,ready,ack,ack_ready,accept,seen_ack,seen_ready;
 wire [15:0] agen;
 wire [95:0] word_out,word_in;
 wire [16:0] prepared;
 wire spi_reset;
 nes_domain_reset124 host_reset(.clk(host_clk),.raw_reset(reset),.reset(spi_reset));
 nes_native_export203 #(.MAX_CYCLES(33554432)) dut(.clk(clk),.reset(reset),.enable(enable),
  .frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),.patch_count(patches),
  .row_count(8'd224),.object_count(objects),.exception_count(exceptions),.group_count(groups),.palette_count(palettes),
  .release_frame(released),.query(query),.query_kind(kind),.query_index(index),.query_generation(qgen),
  .response(response),.hit(1'b1),.data(data),.tx_valid(send),.tx_ready(can_send),.tx_data(word_out),
  .ack_valid(seen_ack),.ack_accept(prepared[16]),.ack_generation(prepared[15:0]),.ack_ready(seen_ready),
  .observe_state177(),.busy(busy),.error(source_fault));
 nes_native_mailbox165 #(.WIDTH(96)) records(.src_clk(clk),.dst_clk(host_clk),.reset(reset),
  .src_valid(send),.src_ready(can_send),.src_data(word_out),.dst_valid(valid),.dst_ready(ready),.dst_data(word_in));
 nes_native_mailbox165 #(.WIDTH(17)) acknowledgments(.src_clk(host_clk),.dst_clk(clk),.reset(reset),
  .src_valid(ack),.src_ready(ack_ready),.src_data({accept,agen}),.dst_valid(seen_ack),.dst_ready(seen_ready),.dst_data(prepared));
 nes_native_spi165 spi(.clk(host_clk),.reset(spi_reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .selected(selected),.miso(miso),.record_valid(valid),.record_ready(ready),.record_data(word_in),
  .ack_valid(ack),.ack_ready(ack_ready),.ack_accept(accept),.ack_generation(agen),.fault(host_fault));
 integer origin_ns=0,first_ns=0,row_queries=0;
 always @(posedge spi.sealed) if(!first_ns)first_ns=$rtoi($realtime)-origin_ns;
 always @(posedge clk)begin
  if(reset)begin row_queries<=0;first_ns<=0;end
  else if(query && kind==1)row_queries<=row_queries+1;
 end
