// SPDX-License-Identifier: MIT
// NES-clock plan -> qualified immutable CHR-ROM reads -> SNES tile bytes.
// Epoch is latched with geometry at capture start by the caller, not at upload.
// Current physical map is 0x200000..0x21ffff; mutable sources need a snapshot.
// Common reset also resets the physical reader. STOP drains it, never resets it.
module nes_source_tile192 #(
 parameter integer MAX_CYCLES=1048576,
 parameter integer USE_CACHE=1
)(
 input wire clk,reset,stop,frame_owned,geometry_valid,
 input wire [15:0] frame_generation,
 input wire source_ready,source_is_rom,source_writing,
 input wire [31:0] captured_epoch,live_epoch,
 input wire plan_valid,output wire plan_ready,input wire [1:0] plan_kind,
 input wire [15:0] plan_generation,input wire [9:0] plan_slot,
 input wire [12:0] plan_tag,input wire [47:0] plan_rows,
 input wire [7:0] plan_mask,plan_alt_mask,input wire [103:0] plan_alt_tags,
 input wire qualified_slot,core_safe,core_request,input wire [21:0] core_address,
 output wire core_ready,core_response,core_error,
 output wire [21:0] core_response_address,output wire [7:0] core_data,
 input wire mem_ready,mem_response,mem_error,input wire [21:0] mem_response_address,
 input wire [7:0] mem_data,output wire mem_request,output wire [21:0] mem_address,
 output wire out_valid,input wire out_ready,output wire [7:0] out_data,
 output wire [4:0] out_index,output wire [5:0] out_length,
 output wire [1:0] out_kind,output wire [9:0] out_slot,output wire [15:0] out_generation,
 output wire busy,done,fault,drained
);
 wire immutable=source_ready&&source_is_rom&&!source_writing&&captured_epoch==live_epoch;
 wire lease=frame_owned&&geometry_valid&&immutable;
 wire tile_request,tile_cancel,tile_ready,tile_response,tile_error,tile_idle;
 wire [16:0] tile_address;wire [15:0] tile_generation,reply_generation;
 wire [21:0] reply_address;wire [7:0] reply_data;
 wire tile_fault,arbiter_fault;
 reg denied;
 // Refuse unsupported input rather than silently stalling forever. STOP is
 // recovery; a memory content epoch must never wrap while a frame is retained.
 always @(posedge clk)begin
  if(reset||stop)denied<=0;
  else if((frame_owned&&!immutable)||(plan_valid&&!lease))denied<=1;
 end
 assign fault=denied||tile_fault||arbiter_fault;
 wire ready_internal;
 assign plan_ready=ready_internal&&!fault;
 wire arb_request,arb_abort,arb_ready,arb_idle,arb_response,arb_error;
 wire [21:0] arb_address,arb_reply_address;wire [15:0] arb_generation,arb_reply_generation;wire [7:0] arb_data;
 // Drained reports the shared physical reader, including STOP/flush cycles.
 assign drained=arb_idle;
 generate if(USE_CACHE)begin:cache_path
  nes_chr_cache192 cache(.clk(clk),.reset(reset),.flush(tile_cancel||denied||!immutable),.content_epoch(live_epoch),
   .request(tile_request),.address({5'h10,tile_address}),.generation(tile_generation),
   .ready(tile_ready),.idle(tile_idle),.response(tile_response),.error(tile_error),
   .response_address(reply_address),.response_generation(reply_generation),.data(reply_data),
   .back_request(arb_request),.back_abort(arb_abort),.back_address(arb_address),.back_generation(arb_generation),
   .back_ready(arb_ready),.back_idle(arb_idle),.back_response(arb_response),.back_error(arb_error),
   .back_response_address(arb_reply_address),.back_response_generation(arb_reply_generation),.back_data(arb_data));
 end else begin:no_cache
  assign arb_request=tile_request;assign arb_abort=tile_cancel||denied;
  assign arb_address={5'h10,tile_address};assign arb_generation=tile_generation;
  assign tile_ready=arb_ready;assign tile_idle=arb_idle;assign tile_response=arb_response;assign tile_error=arb_error;
  assign reply_address=arb_reply_address;assign reply_generation=arb_reply_generation;assign reply_data=arb_data;
 end endgenerate
 nes_tile191 #(.MAX_CYCLES(MAX_CYCLES)) tile(
  .clk(clk),.reset(reset),.stop(stop),.lease_valid(lease&&!fault),.lease_generation(frame_generation),
  .plan_valid(plan_valid&&!fault),.plan_ready(ready_internal),.plan_kind(plan_kind),
  .plan_generation(plan_generation),.plan_slot(plan_slot),.plan_tag(plan_tag),.plan_rows(plan_rows),
  .plan_mask(plan_mask),.plan_alt_mask(plan_alt_mask),.plan_alt_tags(plan_alt_tags),
  .mem_idle(tile_idle),.mem_ready(tile_ready),.mem_request(tile_request),.mem_cancel(tile_cancel),
  .mem_address(tile_address),.mem_generation(tile_generation),.mem_response(tile_response),
  .mem_error(tile_error||reply_address[21:17]!=5'h10),.response_address(reply_address[16:0]),
  .response_generation(reply_generation),.response_data(reply_data),
  .out_valid(out_valid),.out_ready(out_ready),.out_data(out_data),.out_index(out_index),
  .out_length(out_length),.out_kind(out_kind),.out_slot(out_slot),.out_generation(out_generation),
  .busy(busy),.fault(tile_fault),.done(done));
 nes_native_arbiter165 arbiter(
  .clk(clk),.reset(reset),.slot(qualified_slot),.core_safe(core_safe),
  .core_request(core_request),.core_address(core_address),.core_ready(core_ready),
  .core_response(core_response),.core_error(core_error),.core_response_address(core_response_address),.core_data(core_data),
  .fill_request(arb_request),.fill_abort(arb_abort),.fill_address(arb_address),.fill_generation(arb_generation),
  .fill_ready(arb_ready),.fill_idle(arb_idle),.fill_response(arb_response),.fill_error(arb_error),
  .fill_response_address(arb_reply_address),.fill_response_generation(arb_reply_generation),.fill_data(arb_data),
  .mem_ready(mem_ready),.mem_request(mem_request),.mem_address(mem_address),.mem_response(mem_response),
  .mem_error(mem_error),.mem_response_address(mem_response_address),.mem_data(mem_data),.fault(arbiter_fault));
endmodule
