module nes_joint257(output wire capture_materialized366,input wire [33:0] read359,output wire ready359,private359,input wire [7:0] expected_data332,output wire [8:0] expected_addr332,input wire plan_zero319,plan_step319,output wire [9:0] plan_cursor319,input wire exec_start298,input wire [1:0] exec_kind298,
 input wire [3:0] exec_op298,input wire [8:0] exec_length298,
 input wire [7:0] exec_data298,output wire exec_busy298,exec_done298,
 output wire [7:0] exec_addr298,
input wire crc_reset287,v_descriptor287,output wire [8:0] manifest_at282,output wire manifest_started282,output wire [2:0] source_raw278,
input wire grant278,
input wire [31:0] grant_epoch278,
input wire [31:0] grant_serial278,
input wire [15:0] grant_generation278,
input wire [2:0] grant_raw278,
input wire host_ack278,
output wire crc_done278,
output wire [3:0] crc_index278,
output wire init278,

 input wire [113:0] link270,output wire [199:0] status270,output wire crc_take270,
input wire display_write,display_request,output wire display_request_ready,
 output wire display_response_valid,input wire display_response_ready,output wire [7:0] display_response,
 input wire v_begin_valid,
input wire v_target_bank,
input wire [2:0] v_raw_count,
input wire v_range_valid,
input wire v_map_range,
input wire [11:0] v_first,
input wire [11:0] v_count,
input wire v_check_valid,
input wire [7:0] v_check_value,
input wire v_finish_valid,
input wire v_all_consumed,
input wire v_display_ack,
output wire v_ready,
output wire v_sealed,
input wire h_start,
input wire [1:0] h_kind,
input wire [3:0] h_index,
input wire h_valid,
input wire [7:0] h_data,
output wire h_ready,
input wire context_valid,
input wire [7:0] context_data,
output wire context_ready,
output wire output_phase,
input wire clk,
input wire reset,
input wire abort_source,
input wire start,
output wire start_ready,
input wire frame_owned,
input wire geometry_valid,
input wire [15:0] frame_generation,
input wire [31:0] content_epoch,
input wire [31:0] frame_serial,
input wire [2:0] patch_count,
output wire done,
output wire [3:0] fault,

input wire stream_valid,input wire [7:0] stream_data,output wire stream_ready,
output wire sink_valid,input wire sink_ready,output wire [7:0] sink_data,
output wire [1:0] sink_kind,output wire [11:0] sink_unit,output wire [4:0] sink_lane,


 input wire display_lease,input wire [15:0] display_generation,input wire [31:0] display_epoch,
 input wire range_external,range_dma_done,
input wire host_clk,SPI_SS,SPI_SCK,SPI_MOSI,
output wire selected,miso,
input wire [7:0] row_count,object_count,exception_count,
input wire [5:0] group_count,palette_count,
output wire query,
output wire [2:0] query_kind,
output wire [12:0] query_index,
output wire [15:0] query_generation,
input wire response,hit,
input wire [63:0] data);

 wire [7:0] ram_a_q,ram_b_q;wire [9:0] ram_a_addr,ram_b_addr;
 wire ram_a_we,ram_b_we;wire [7:0] ram_a_w,ram_b_w;
 (* ramstyle="M9K" *) reg [7:0] memory[0:1023];reg [7:0] aq,bq;
 assign ram_a_q=aq;assign ram_b_q=bq;
 always @(posedge clk)begin aq<=memory[ram_a_addr];if(ram_a_we&&!fault)memory[ram_a_addr]<=ram_a_w;end
 always @(posedge host_clk)begin bq<=memory[ram_b_addr];if(ram_b_we&&!fault)memory[ram_b_addr]<=ram_b_w;end
 wire transport_crc_pending,transport_empty;wire [15:0] transport_crc,crc_result;wire [7:0] transport_byte;
 wire in_valid,in_ready;wire [7:0] in_data;wire [12:0] in_offset;
 wire raw_query;wire [12:0] raw_index;
 wire raw_response=response,raw_hit=hit;wire [63:0] raw_data=data;
 wire record_valid,record_ready,record_flush,byte_valid,byte_ready;
 wire [7:0] record_length,byte_data;wire ack_valid,ack_ready,ack_accept;wire [15:0] ack_generation;
 wire csr,qsr,qd,rquery,sf,hf;wire [2:0] rkind;wire [12:0] rindex;wire [15:0] rgen;
 wire [3:0] cf,qf,vf278;wire cancel=abort_source||fault!=0;wire sealed_raw;
 wire [3:0] discovered=vf278?vf278:cf?cf:sf||hf?4'd8:4'd0;
 reg [3:0] first_fault;
 always @(posedge clk)if(reset)first_fault<=0;else if(!first_fault&&discovered)first_fault<=discovered;
 assign fault=first_fault?first_fault:discovered;
 assign v_sealed=sealed_raw&&!fault&&!abort_source&&display_lease&&output_phase;
 reg [1:0] init_sync278;
 always @(posedge clk or posedge reset)if(reset)init_sync278<=0;else init_sync278<={init_sync278[0],init278};
 assign start_ready=csr&&!fault&&init_sync278[1];
wire record_last319;
nes_core257 encoder(.capture_materialized366(capture_materialized366),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.plan_cursor319(plan_cursor319),.record_last319(record_last319),.source_raw278(source_raw278),.display_write(display_write),.display_request(display_request),.display_request_ready(),
 .display_response_valid(),.display_response_ready(display_response_ready),.display_response(),.display_lease(display_lease),.display_generation(display_generation),.display_epoch(display_epoch),.range_external(range_external),.range_dma_done(range_dma_done),.stream_valid(stream_valid),.stream_data(stream_data),.stream_ready(),.sink_valid(),.sink_ready(sink_ready),.sink_data(),.sink_kind(),.sink_unit(),.sink_lane(),.row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.palette_count(palette_count),.query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.ram_a_q(ram_a_q),.ram_b_q(8'd0),.ram_a_addr(ram_a_addr),.ram_b_addr(),.ram_a_we(ram_a_we),.ram_b_we(),.ram_a_w(ram_a_w),.ram_b_w(),.v_begin_valid(v_begin_valid),.v_target_bank(v_target_bank),.v_raw_count(v_raw_count),.v_range_valid(v_range_valid),.v_map_range(v_map_range),.v_first(v_first),.v_count(v_count),.v_check_valid(v_check_valid),.v_check_value(v_check_value),.v_finish_valid(v_finish_valid),.v_all_consumed(v_all_consumed),.v_display_ack(v_display_ack),.v_ready(),.v_sealed(),.h_start(h_start),.h_kind(h_kind),.h_index(h_index),.h_valid(h_valid),.h_data(h_data),.h_ready(),.context_valid(context_valid),.context_data(context_data),.context_ready(),.transport_crc_pending(transport_crc_pending),.transport_empty(transport_empty),.transport_crc(transport_crc),.transport_byte(transport_byte),.crc_result(crc_result),.output_phase(output_phase),.clk(clk),.reset(reset),.abort_source(cancel),.start(start&&start_ready),.start_ready(csr),.frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(frame_generation),.content_epoch(content_epoch),.frame_serial(frame_serial),.patch_count(patch_count),.in_valid(in_valid),.in_ready(in_ready),.in_data(in_data),.in_offset(in_offset),.raw_query(raw_query),.raw_index(raw_index),.raw_response(raw_response),.raw_hit(raw_hit),.raw_data(raw_data),.record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),.byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_generation),.done(done),.fault(cf));
nes_validator278 validator(.read359(read359),.ready359(ready359),.private359(private359),.expected_data332(expected_data332),.expected_addr332(expected_addr332),.exec_start298(exec_start298),.exec_kind298(exec_kind298),.exec_op298(exec_op298),.exec_length298(exec_length298),.exec_data298(exec_data298),.exec_busy298(exec_busy298),.exec_done298(exec_done298),.exec_addr298(exec_addr298),.crc_reset287(crc_reset287),.v_descriptor287(v_descriptor287),.manifest_at282(manifest_at282),.manifest_started282(manifest_started282),.grant278(grant278),.grant_epoch278(grant_epoch278),.grant_serial278(grant_serial278),.grant_generation278(grant_generation278),.grant_raw278(grant_raw278),.host_ack278(host_ack278),.crc_done278(crc_done278),.crc_index278(crc_index278),.init278(init278),.display_write(display_write),.display_request(display_request),.display_request_ready(display_request_ready),.display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),.v_begin_valid(v_begin_valid),.v_target_bank(v_target_bank),.v_raw_count(v_raw_count),.v_range_valid(v_range_valid),.v_map_range(v_map_range),.v_first(v_first),.v_count(v_count),.v_check_valid(v_check_valid),.v_check_value(v_check_value),.v_finish_valid(v_finish_valid),.v_all_consumed(v_all_consumed),.v_ready(v_ready),.h_start(h_start),.h_kind(h_kind),.h_index(h_index),.legacy_h_valid(h_valid),.legacy_h_data(h_data),.h_ready(h_ready),.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),
 .clk(host_clk),.reset(reset),.abort_source(cancel),.fault(vf278),.v_sealed(sealed_raw),
 .ram_q(ram_b_q),.ram_addr(ram_b_addr),.ram_we(ram_b_we),.ram_w(ram_b_w));
assign stream_ready=0;assign sink_valid=0;assign sink_data=0;
 assign sink_kind=0;assign sink_unit=0;assign sink_lane=0;
nes_transport257 #(.SPLIT_CREDIT371(1)) transport(.record_last319(record_last319),.frame_generation(frame_generation),.link270(link270),.status270(status270),.crc_take270(crc_take270),.crc_result(crc_result),.crc_pending(transport_crc_pending),.crc_previous(transport_crc),.crc_byte(transport_byte),.src_clk(clk),.host_clk(host_clk),.reset(reset),.abort_source(cancel),.record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),.byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(selected),.miso(miso),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_accept),.ack_generation(ack_generation),.source_fault(sf),.host_fault(hf),.source_empty(transport_empty));
endmodule
