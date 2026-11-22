// SPDX-License-Identifier: MIT
// Between the capture-cache MISS port and the existing core-priority arbiter.
// Cached data is an exact low/high plane pair from a single physical read.
module nes_e9_rows914 #(parameter COMPACT=0, CHECK_HINT=0, SINGLE_READ=0, COMPLETE_ROW_SET=0)(
 input wire clk, reset, invalidate, hint, input wire [12:0] tag,
 input wire [7:0] mask, output wire hint_ready,
 input wire demand, pair, input wire [21:0] address,
 output wire ready, response, output wire [7:0] lo,hi,
 output wire request, output wire [21:0] physical_address,
 input wire grant_ready, reply, physical_done, physical_error,
 input wire [21:0] reply_address, input wire [7:0] physical_lo,physical_hi
);
 function automatic [6:0] cache_index(input [21:0] a);
  cache_index={a[7:4]^(CHECK_HINT?a[8:5]:a[14:11]),a[2:0]};
 endfunction
 // Given the RAM index and tag[12:4], tag[3:0] is uniquely recoverable.
 localparam LOW=COMPACT?4:0, WIDTH=30-LOW;
 (* ramstyle="M9K, no_rw_check" *) reg [WIDTH-1:0] rows[0:127];
 reg [WIDTH-1:0] lookup;
 reg [7:0] scrub;
 reg [12:0] hint_tag;
 reg [7:0] todo;
 reg [2:0] row_no;
 reg armed, spec_owner, discarded, checked, hit_reply, demand_pair;
 wire live=!invalidate&&!reset&&scrub[7];
 assign hint_ready=live&&todo==0&&!spec_owner;
 wire candidate=pair&&!address[3]&&live;
 wire hit=candidate&&checked&&lookup[WIDTH-1]&&lookup[WIDTH-2:16]==address[16:4+LOW];
 wire foreground=demand&&(!candidate||(checked&&!hit));
 wire needed=COMPACT?todo[0]:todo[row_no];
 wire [21:0] hint_address={5'h10,hint_tag,1'b0,row_no};
 reg spec_checked;
 wire inspect=live&&armed&&!demand&&!hit_reply&&needed&&!spec_owner&&!reply;
 wire redundant=CHECK_HINT&&inspect&&spec_checked&&lookup[WIDTH-1]&&
                lookup[WIDTH-2:16]==hint_tag[12:LOW];
 wire spec=live&&armed&&!demand&&!hit_reply&&needed&&!spec_owner&&
           (!CHECK_HINT||(inspect&&spec_checked&&!redundant));
 assign request=foreground||spec;
 assign physical_address=spec?hint_address:address;
 wire take=request&&grant_ready;
 assign ready=demand&&(hit||(foreground&&grant_ready));
 assign response=(hit_reply&&live)||(reply&&!spec_owner);
 assign lo=hit_reply?lookup[7:0]:physical_lo;
 assign hi=hit_reply?lookup[15:8]:physical_hi;
 wire lookup_demand=demand&&!checked&&!spec_owner;
 wire lookup_hint=CHECK_HINT&&inspect&&!spec_checked;
 generate if(SINGLE_READ)begin
  wire [6:0] index=lookup_demand?cache_index(address):cache_index(hint_address);
  always @(posedge clk)if(lookup_demand||lookup_hint)lookup<=rows[index];
 end else begin
  always @(posedge clk)
   if(lookup_demand)lookup<=rows[cache_index(address)];
   else if(lookup_hint)lookup<=rows[cache_index(hint_address)];
 end endgenerate
 always @(posedge clk)begin
  spec_checked<=inspect&&!redundant&&!(take&&spec);
  if(reset||invalidate) scrub<=0;
  else if(!scrub[7])scrub<=scrub+1'b1;
  if(!scrub[7])rows[scrub[6:0]]<=0;
  else if(live&&reply&&!physical_error&&(COMPACT||!discarded)&&
          (spec_owner||(COMPACT?(pair&&!reply_address[3]):demand_pair)))
   rows[cache_index(reply_address)]<={1'b1,reply_address[16:4+LOW],physical_hi,physical_lo};
  // Only a physical completion (or common reader reset) releases this owner.
  if(reset)begin spec_owner<=0;discarded<=0;demand_pair<=0;end
  else begin
   if(invalidate)discarded<=1;
   if(physical_done)begin spec_owner<=0;demand_pair<=0;end
   if(take)begin spec_owner<=spec;demand_pair<=!spec&&candidate;discarded<=0;end
  end
  if(!live)begin
   todo<=0;row_no<=0;armed<=0;checked<=0;hit_reply<=0;
  end else begin
   checked<=demand&&candidate&&!spec_owner&&!ready;
   hit_reply<=demand&&hit;
   if(take&&!spec&&candidate)armed<=1;
   if(hint&&hint_ready)begin
    hint_tag<=tag;todo<=(COMPLETE_ROW_SET&&(&mask[3:0]))?8'hff:mask;row_no<=0;
   end
   else if(todo!=0&&(!needed||redundant||(take&&spec)))begin
    if(COMPACT)todo<=todo>>1;else todo[row_no]<=0;
    row_no<=row_no+1'b1;
   end
  end
 end
endmodule
