// SPDX-License-Identifier: MIT
// Diagnostic NES-clock lookup. Source addresses are physical CHR-ROM offsets.
// A miss requires the ordinary qualified reader. A sample is never backpressure
// to the PPU. Caller qualifies its data/plane/strobe and capture ownership.
module nes_chr_snoop601 (
 input wire clk, reset, stop, immutable, capture_open, query_owned,
 input wire [31:0] content_epoch,
 input wire sample, sample_obj, input wire [16:0] sample_address,
 input wire [7:0] sample_data, output wire sample_ready,
 input wire query, query_obj, input wire [16:0] query_address,
 output wire query_ready, response, hit, output wire [7:0] data
);
 (* ramstyle="M9K" *) reg [21:0] directory[0:255]; // physical tag high 6, lane-valid 16
 (* ramstyle="M9K" *) reg [7:0] bytes[0:4095];
 reg [31:0] epoch;
 reg clearing, pending, replying;
 reg [7:0] clear_index, held_line, held_byte;
 reg [5:0] held_tag;
 reg [3:0] held_lane;
 reg [21:0] entry;
 reg [7:0] read_data;
 wire live=!reset&&!stop&&immutable&&epoch==content_epoch;
 wire active=live&&!clearing;
 assign sample_ready=active&&capture_open&&!query_owned&&!pending;
 assign query_ready=active&&query_owned&&!capture_open&&!pending;
 wire accept=sample&&sample_ready;
 wire lookup=query&&query_ready;
 wire [16:0] addr=capture_open?sample_address:query_address;
 wire [7:0] line={capture_open?sample_obj:query_obj,addr[10:4]};
 wire same_tag=entry[21:16]==held_tag;
 wire [15:0] updated=(same_tag?entry[15:0]:16'b0)|(16'h1<<held_lane);
 assign response=replying&&query_ready;
 assign hit=response&&same_tag&&entry[held_lane];
 assign data=read_data; // meaningful only alongside hit

 // Each sample first reads the directory then commits data and mask together.
 // Adjacent capture strobes are at least two clocks apart in the replay.
 always @(posedge clk) begin
  if(accept||lookup)begin
   entry<=directory[line];
   held_tag<=addr[16:11]; held_lane<=addr[3:0];
  end
  if(accept)begin held_line<=line; held_byte<=sample_data; end
  if(lookup)read_data<=bytes[{line,addr[3:0]}];
  if(live&&clearing)directory[clear_index]<=0;
  else if(active&&pending)begin
   directory[held_line]<={held_tag,updated};
   bytes[{held_line,held_lane}]<=held_byte;
  end
  epoch<=content_epoch;
  if(!live)begin clearing<=1; clear_index<=0; pending<=0; replying<=0; end
  else begin
   if(clearing)begin
    clear_index<=clear_index+1'b1;
    if(&clear_index)clearing<=0;
   end
   pending<=accept;
   replying<=lookup;
  end
 end
endmodule
