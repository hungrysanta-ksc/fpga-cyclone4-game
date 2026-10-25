// SPDX-License-Identifier: MIT
module nes_joint267_board #(parameter SHARED=1)(output wire capture_materialized366,input wire plan_zero319,plan_step319,output wire [9:0] plan_cursor319,output wire queue_admit319,input wire [113:0] link270,output wire [199:0] source_status270,output_status270,
 output wire source_crc270,output_crc270,












output wire  v_ready,
output wire  v_sealed,





output wire  h_ready,


output wire  context_ready,
output wire  output_phase,
input wire  clk,
input wire  reset,
input wire  abort_source,
input wire  start,
output wire  start_ready,
input wire  frame_owned,
input wire  geometry_valid,
input wire [15:0] frame_generation,
input wire [31:0] content_epoch,
input wire [31:0] frame_serial,
input wire [2:0] patch_count,
output wire  done,
output wire [3:0] fault,


output wire  stream_ready,
output wire  sink_valid,
input wire  sink_ready,
output wire [7:0] sink_data,
output wire [1:0] sink_kind,
output wire [11:0] sink_unit,
output wire [4:0] sink_lane,
input wire  host_clk,
input wire  SPI_SS,
input wire  SPI_SCK,
input wire  SPI_MOSI,
output wire  selected,
output wire  miso,
input wire [7:0] row_count,
input wire [7:0] object_count,
input wire [7:0] exception_count,
input wire [5:0] group_count,
input wire [5:0] palette_count,
output wire  query,
output wire [2:0] query_kind,
output wire [12:0] query_index,
output wire [15:0] query_generation,
input wire  response,
input wire  hit,
input wire [63:0] data,
input wire capture_begin,source_ready,source_is_rom,source_writing,reader_drained,
output wire release_frame,retired,display_ack,
input wire lease_valid,waiting_display,lease_fault,
output wire tile_closed267,
input wire identity_valid,output wire identity_ready,input wire bank,
input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
output wire [7:0] data_out,output wire bus_valid,staged,receipt_committed,flow_fault,
input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data,
input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind,
input wire [9:0] tile_slot,input wire [15:0] tile_generation,
input wire end_valid,end_partial295,output wire end_ready,input wire [15:0] end_generation,
output wire ordinary_ready,output wire [31:0] next_token
);

wire [8:0] manifest_at282;wire manifest_started282;
wire [2:0] source_raw278;
wire grant278;
wire [31:0] grant_epoch278;
wire [31:0] grant_serial278;
wire [15:0] grant_generation278;
wire [2:0] grant_raw278;
wire host_ack278;
wire crc_done278;
wire [3:0] crc_index278;
wire init278;
 wire [7:0] expected_data332;wire [8:0] expected_addr332;
 wire display_write,display_request,display_request_ready,display_response_valid,display_response_ready;
 wire [7:0] display_response;
 wire v_begin_valid,v_target_bank,context_valid;wire [2:0] v_raw_count;wire [7:0] context_data;
 wire  v_range_valid;
 wire  v_map_range;
 wire [11:0] v_first;
 wire [11:0] v_count;
 wire  v_check_valid;
 wire [7:0] v_check_value;
 wire  v_finish_valid;
 wire  v_all_consumed;
 wire  stream_valid;
 wire [7:0] stream_data;
 wire  h_start;
 wire [1:0] h_kind;
 wire [3:0] h_index;
 wire  h_valid;
 wire [7:0] h_data;
 assign v_map_range=0;
 assign stream_data=v_check_value;assign h_data=v_check_value;
 wire [15:0] display_generation;wire [31:0] display_epoch;
 reg ordinary_done;
 always @(posedge clk or posedge reset)begin
  if(reset)ordinary_done<=0;else ordinary_done<=v_range_valid&&v_ready&&!abort_source&&!flow_fault&&!lease_fault;
 end
 wire rv,rdone;wire [11:0] rf,rc;
 wire source_selected,source_miso,output_selected,output_miso;
 wire cancel=abort_source||flow_fault||lease_fault;
 assign selected=source_selected||output_selected;
 assign miso=source_selected?source_miso:output_miso;
 assign display_generation=frame_generation;assign display_epoch=content_epoch;
 assign release_frame=1'b0;

wire exec_start298,exec_busy298,exec_done298;wire [1:0] exec_kind298;
 wire [3:0] exec_op298;wire [8:0] exec_length298;wire [7:0] exec_data298,exec_addr298;
 wire crc_reset287;
 wire [33:0] read359;wire ready359,private359;
 nes_output260 #(.SHARED(SHARED)) flow(.read359(read359),.ready359(ready359),.private359(private359),.jobs_committed336(v_all_consumed),.expected_data332(expected_data332),.expected_addr332(expected_addr332),.queue_admit319(queue_admit319),.exec_start298(exec_start298),.exec_kind298(exec_kind298),.exec_op298(exec_op298),.exec_length298(exec_length298),.exec_data298(exec_data298),.exec_busy298(exec_busy298),.exec_done298(exec_done298),.exec_addr298(exec_addr298),.crc_reset287(crc_reset287),.manifest_at282(manifest_at282),.manifest_started282(manifest_started282),.grant278(grant278),.grant_epoch278(grant_epoch278),.grant_serial278(grant_serial278),.grant_generation278(grant_generation278),.grant_raw278(grant_raw278),.host_ack278(host_ack278),.crc_done278(crc_done278),.crc_index278(crc_index278),.init278(init278),.epoch278(content_epoch),.raw278(source_raw278),.link270(link270),.status270(output_status270),.crc_take270(output_crc270),.display_write(display_write),.display_request(display_request),.display_request_ready(display_request_ready),
 .display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),.nes_clk(clk),.host_clk(host_clk),.reset(reset),.cancel(abort_source||lease_fault||fault!=0),
 .tile_closed267(tile_closed267),.identity_valid(identity_valid&&output_phase),.identity_ready(identity_ready),.serial(frame_serial),.generation(display_generation),.bank(bank),
 .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.miso(output_miso),.selected(output_selected),
 .address(address),.read_n(read_n),.write_n(write_n),.data_in(data_in),.data_out(data_out),.bus_valid(bus_valid),
 .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),
 .tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
 .end_valid(end_valid),.end_partial295(end_partial295),.end_ready(end_ready),.end_generation(end_generation),
 .range_valid(rv),.range_ready(v_ready),.range_first(rf),.range_count(rc),.range_dma_done(rdone),
 .sealed(v_sealed),.core_idle(start_ready),.display_ack(display_ack),.retired(retired),.staged(staged),
 .receipt_committed(receipt_committed),.fault(flow_fault),
 .context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),
 .ordinary_range(v_range_valid),.ordinary_first(v_first),.ordinary_end300(v_count),
 .ordinary_stream(stream_valid),.ordinary_byte(v_check_value),.ordinary_stream_ready(stream_ready),
 .ordinary_check(v_check_valid),.ordinary_finish(v_finish_valid),.ordinary_hash_start(h_start),.ordinary_hash_byte(h_valid),
 .ordinary_hash_kind(h_kind),.ordinary_hash_index(h_index),.ordinary_hash_ready(h_ready),
 .begin_valid(v_begin_valid),.begin_bank(v_target_bank),.begin_raw(v_raw_count),.ordinary_ready(ordinary_ready),.next_token(next_token));
nes_joint257 core(.capture_materialized366(capture_materialized366),.read359(read359),.ready359(ready359),.private359(private359),.expected_data332(expected_data332),.expected_addr332(expected_addr332),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.plan_cursor319(plan_cursor319),.exec_start298(exec_start298),.exec_kind298(exec_kind298),.exec_op298(exec_op298),.exec_length298(exec_length298),.exec_data298(exec_data298),.exec_busy298(exec_busy298),.exec_done298(exec_done298),.exec_addr298(exec_addr298),.crc_reset287(crc_reset287),.v_descriptor287(v_range_valid),.manifest_at282(manifest_at282),.manifest_started282(manifest_started282),.source_raw278(source_raw278),.grant278(grant278),.grant_epoch278(grant_epoch278),.grant_serial278(grant_serial278),.grant_generation278(grant_generation278),.grant_raw278(grant_raw278),.host_ack278(host_ack278),.crc_done278(crc_done278),.crc_index278(crc_index278),.init278(init278),.link270(link270),.status270(source_status270),.crc_take270(source_crc270),.display_write(display_write),.display_request(display_request),.display_request_ready(display_request_ready),
 .display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),.v_begin_valid(v_begin_valid),
.v_target_bank(v_target_bank),
.v_raw_count(v_raw_count),
.v_range_valid(v_range_valid||rv),
.v_map_range(rv?1'b1:v_map_range),
.v_first(rv?rf:v_first),
.v_count(rv?rc:v_count),
.v_check_valid(v_check_valid),
.v_check_value(v_check_value),
.v_finish_valid(v_finish_valid),
.v_all_consumed(v_all_consumed),
.v_display_ack(display_ack),
.v_ready(v_ready),
.v_sealed(v_sealed),
.h_start(h_start),
.h_kind(h_kind),
.h_index(h_index),
.h_valid(h_valid),
.h_data(h_data),
.h_ready(h_ready),
.context_valid(context_valid),
.context_data(context_data),
.context_ready(context_ready),
.output_phase(output_phase),
.clk(clk),
.reset(reset),
.abort_source(cancel),
.start(start),
.start_ready(start_ready),
.frame_owned(frame_owned),
.geometry_valid(geometry_valid),
.frame_generation(frame_generation),
.content_epoch(content_epoch),
.frame_serial(frame_serial),
.patch_count(patch_count),
.done(done),
.fault(fault),
.stream_valid(stream_valid),
.stream_data(stream_data),
.stream_ready(stream_ready),
.sink_valid(sink_valid),
.sink_ready(sink_ready),
.sink_data(sink_data),
.sink_kind(sink_kind),
.sink_unit(sink_unit),
.sink_lane(sink_lane),
.display_lease(lease_valid),
.display_generation(display_generation),
.display_epoch(display_epoch),
.range_external(1'b1),
.range_dma_done(rdone||ordinary_done),
.host_clk(host_clk),
.SPI_SS(SPI_SS),
.SPI_SCK(SPI_SCK),
.SPI_MOSI(SPI_MOSI),
.selected(source_selected),
.miso(source_miso),
.row_count(row_count),
.object_count(object_count),
.exception_count(exception_count),
.group_count(group_count),
.palette_count(palette_count),
.query(query),
.query_kind(query_kind),
.query_index(query_index),
.query_generation(query_generation),
.response(response),
.hit(hit),
.data(data));
endmodule
