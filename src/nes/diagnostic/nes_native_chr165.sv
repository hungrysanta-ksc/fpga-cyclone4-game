// SPDX-License-Identifier: MIT
// Passive SMB3 CHR-ROM mirror. No ROM request, stall, or game-state outputs.
// Single NES-clock interface; a host CDC/lease bridge is NOT included here.
// Logical tile slots carry physical tags and a 16-byte validity mask. A bank
// change invalidates the old tile before its first byte becomes observable.
module nes_native_chr165(
 input wire clk,reset,
 input wire sample,sample_valid,
 input wire [12:0] logical_address,
 input wire [21:0] physical_address,
 input wire [7:0] sample_data,
 input wire freeze,release_cache,
 output reg initialized,owned,
 input wire query,input wire [8:0] query_slot,
 input wire [17:0] query_tag,input wire [4:0] query_offset,
 input wire query_obj4,
 output reg response,hit,output reg [7:0] data,
 output reg [15:0] valid_bytes
);
 // 8192 bytes and 512 x (18-bit tag + 16-bit mask). Array sizes are logical;
 // actual M9K/LAB use and timing require synthesis in the replacement design.
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] bytes_mem[0:8191];
 (* ramstyle="M9K, no_rw_check" *) reg [33:0] metadata[0:511];
 reg [8:0] scrub;
 reg draining;
 reg pending;
 reg [8:0] slot_q;
 reg [17:0] tag_q;
 reg [3:0] lane_q;
 reg [33:0] read_meta;
 reg committed;
 reg [8:0] committed_slot;
 reg [33:0] committed_meta;
 wire [33:0] previous=(committed && committed_slot==slot_q)?committed_meta:read_meta;
 wire [15:0] mask_next=(previous[33:16]==tag_q?previous[15:0]:16'd0) |
                        (16'h0001<<lane_q);
 wire [33:0] write_meta={tag_q,mask_next};
 // Mapper4 preserves the byte offset within a tile. Reject a malformed tap,
 // palette/CIRAM reads and invalid responses rather than caching them.
 wire accept=!reset && initialized && !owned && !draining && !freeze &&
             sample && sample_valid && physical_address>=22'h200000 &&
             physical_address<22'h220000 &&
             logical_address[3:0]==physical_address[3:0];
 wire [8:0] slot=logical_address[12:4];
 // NES planes are 8-byte separated; SNES plane0/1 are interleaved by row.
 wire [3:0] read_lane={query_offset[0],query_offset[3:1]};
 wire [33:0] query_meta=read_meta;
 reg [7:0] query_byte;
 reg query_pending,query_zero,query_range;
 reg [17:0] expected_tag;
 // Read/write ports contain no asynchronous RAM reset.
 always @(posedge clk)begin
  if(!initialized && !reset)metadata[scrub]<=0;
  else if(pending && !reset)metadata[slot_q]<=write_meta;
  if(accept)begin
   bytes_mem[logical_address]<=sample_data;
  end
  if(accept || (query && owned && !release_cache && !reset))
   read_meta<=metadata[owned?query_slot:slot];
  if(query && owned && !release_cache && !reset)begin
   query_byte<=bytes_mem[{query_slot,read_lane}];
  end
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   initialized<=0;owned<=0;scrub<=0;draining<=0;pending<=0;
   slot_q<=0;tag_q<=0;lane_q<=0;committed<=0;
   committed_slot<=0;committed_meta<=0;
   query_pending<=0;query_zero<=0;query_range<=0;expected_tag<=0;
   response<=0;hit<=0;data<=0;valid_bytes<=0;
  end else begin
   response<=0;pending<=0;committed<=0;query_pending<=0;
   if(!initialized)begin
    if(scrub==511)begin initialized<=1;scrub<=0;end
    else scrub<=scrub+1'b1;
   end else begin
    if(pending)begin committed<=1;committed_slot<=slot_q;committed_meta<=write_meta;end
    if(accept)begin pending<=1;slot_q<=slot;tag_q<=physical_address[21:4];lane_q<=logical_address[3:0];end
    // Freeze wins over a new sample, drains the prior metadata write, then
    // grants a stable lease. A partial tile remains explicitly unavailable.
    if(release_cache)begin owned<=0;draining<=0;query_pending<=0;hit<=0;valid_bytes<=0;end
    else if(!owned && freeze)draining<=1;
    if(draining && !release_cache)begin owned<=1;draining<=0;end
    if(query && owned && !release_cache)begin
     query_pending<=1;expected_tag<=query_tag;
     query_zero<=query_obj4 && query_offset[4];
     query_range<=query_obj4 || !query_offset[4];
    end
    if(query_pending && owned && !release_cache)begin
     response<=1;
     valid_bytes<=query_meta[33:16]==expected_tag?query_meta[15:0]:16'd0;
     hit<=query_range && query_meta[33:16]==expected_tag && (&query_meta[15:0]);
     data<=(query_range && query_meta[33:16]==expected_tag && (&query_meta[15:0]))?
            (query_zero?8'd0:query_byte):8'd0;
    end
   end
  end
 end
endmodule
