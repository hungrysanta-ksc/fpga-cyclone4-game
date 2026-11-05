// SPDX-License-Identifier: MIT
// NES-clock diagnostic. start/release/query use the full capture generation.
// The loader must assert stop on every change of immutable ROM contents.
module nes_obj_capture609 (
 input wire clk, reset, stop, immutable,
 input wire start, seal, release_bank,
 input wire [15:0] capture_gen, release_gen,
 input wire sample, input wire [16:0] sample_address, input wire [7:0] sample_data,
 input wire query, input wire [15:0] query_gen, input wire [16:0] query_address,
 output wire start_ready, sample_ready, query_ready, response, hit, output wire [7:0] data
);
 (* ramstyle="M9K" *) reg [21:0] directory[0:255];
 (* ramstyle="M9K" *) reg [7:0] bytes[0:4095];
 reg [15:0] owner[0:1];
 reg [1:0] held;
 reg capturing, bank, clearing, pending, bad;
 reg [6:0] clear_index;
 reg [16:0] wr_addr;
 reg [7:0] wr_data;
 reg [21:0] entry;
 reg [7:0] fetched;
 reg [3:0] lane;
 reg [5:0] tag;
 reg replied, eligible, reply_bank;
 // Latch even a STOP pulse while the NES clock is stopped. On restart,
 // clear both owners before any new request can observe the old directory.
 wire kill=reset||stop||!immutable;
 reg [1:0] drain;
 always @(posedge clk or posedge kill)
  if(kill) drain<=2'b11;
  else drain<={drain[0],1'b0};
 wire live=!kill&&!drain[1];
 assign start_ready=live&&!capturing&&!held[capture_gen[0]];
 assign sample_ready=live&&capturing&&!clearing&&!pending;
 wire take=sample&&sample_ready;
 // An accepted strobe reserves the next edge for committing its sample.
 // That edge has no capture read, so a held query waits at most one edge.
 assign query_ready=live&&!take;
 wire lookup=query&&query_ready;
 wire [7:0] write_line={bank,clearing?clear_index:wr_addr[10:4]};
 wire [7:0] read_line=take?{bank,sample_address[10:4]}:{query_gen[0],query_address[10:4]};
 wire [15:0] mask=(entry[21:16]==wr_addr[16:11]?entry[15:0]:16'b0)|(16'h1<<wr_addr[3:0]);
 wire owns=held[query_gen[0]]&&owner[query_gen[0]]==query_gen;
 wire retire=release_bank&&held[release_gen[0]]&&owner[release_gen[0]]==release_gen;
 assign response=live&&replied;
 assign hit=response&&eligible&&held[reply_bank]&&!(retire&&release_gen[0]==reply_bank)&&
            entry[21:16]==tag&&entry[lane];
 assign data=fetched;
 always @(posedge clk) begin
  if(live&&capturing&&clearing) directory[write_line]<=0;
  else if(live&&pending) directory[write_line]<={wr_addr[16:11],mask};
  if(take||(lookup&&owns)) entry<=directory[read_line];
  if(live&&pending) bytes[{bank,wr_addr[10:0]}]<=wr_data;
  if(take) begin wr_addr<=sample_address; wr_data<=sample_data; end
  if(lookup&&owns) begin
   fetched<=bytes[{query_gen[0],query_address[10:0]}];
   tag<=query_address[16:11]; lane<=query_address[3:0];
  end
  if(!live) begin
   held<=0; capturing<=0; pending<=0; clearing<=0; replied<=0; eligible<=0; bad<=0;
  end else begin
   replied<=lookup; eligible<=lookup&&owns; reply_bank<=query_gen[0];
   pending<=take;
   if(retire)
    held[release_gen[0]]<=0;
   if(start&&start_ready) begin
    capturing<=1; bank<=capture_gen[0]; owner[capture_gen[0]]<=capture_gen;
    clearing<=1; clear_index<=0; bad<=0;
   end
   if(clearing) begin clear_index<=clear_index+1'b1; if(&clear_index) clearing<=0; end
   if(capturing&&sample&&!sample_ready) bad<=1;
   if(capturing&&seal) begin
    // A pending sample commits at this edge. A newly presented sample or
    // incomplete clear makes this capture ineligible; queries then use ROM.
    held[bank]<=!bad&&!clearing&&!sample;
    capturing<=0; pending<=0; clearing<=0;
   end
  end
 end
endmodule
