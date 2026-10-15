// SPDX-License-Identifier: MIT
// Candidate, NOT wired into the deployed board. Two immutable 2KiB chunks.
// All producer/control ports are in clk domain; the raw SNES read bus is sampled.
// Producer must use a fresh token across STOP/restart; this is not a display ACK.
module nes_bulk_aperture188(
 input wire clk, reset, active, stop,
 input wire begin_valid, input wire [11:0] begin_length,
 input wire [31:0] begin_token, output wire begin_ready,
 input wire byte_valid, input wire [7:0] byte_data, output wire byte_ready,
 input wire seal, cancel,
 output reg producer_error,
 output wire chunk_ready, output wire [11:0] chunk_length,
 output wire [31:0] chunk_token,
 input wire consume, input wire [31:0] consume_token,
 output reg consume_error,
 input wire [23:0] address, input wire read_n, write_n,
 output wire [7:0] data_out, output wire oe_n, dir
);
 // Candidate bank40:0800..0fff; existing packet window is bank40:0000..00ff.
 // Top-level decode/physical timing and descriptor/control mapping remain gated.
 (* ramstyle="M9K" *) reg [7:0] storage[0:4095];
 reg [1:0] sealed;
 reg writer, reader, filling;
 reg [11:0] count, wanted;
 reg [31:0] pending_token;
 reg [11:0] lengths[0:1];
 reg [31:0] tokens[0:1];
 wire local_reset;
 nes_domain_reset124 release_local(.clk(clk),.raw_reset(reset||stop||!active),.reset(local_reset));
 wire enabled=active&&!reset&&!stop&&!local_reset;
 assign begin_ready=enabled&&!seal&&!cancel&&!filling&&!sealed[writer];
 assign byte_ready=enabled&&!seal&&!cancel&&filling&&count<wanted;
 assign chunk_ready=enabled&&sealed[reader];
 assign chunk_length=chunk_ready?lengths[reader]:12'd0;
 assign chunk_token=chunk_ready?tokens[reader]:32'd0;

 // Separate write and read ports. Memory payload is never reset or exposed
 // until every declared byte was written and a later seal publishes it.
 always @(posedge clk)
  if(byte_valid&&byte_ready&&!cancel&&!seal)
   storage[{writer,count[10:0]}]<=byte_data;

 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin
   sealed<=0;writer<=0;reader<=0;filling<=0;count<=0;wanted<=0;
   pending_token<=0;lengths[0]<=0;lengths[1]<=0;tokens[0]<=0;tokens[1]<=0;
   producer_error<=0;consume_error<=0;
  end else begin
   producer_error<=0;consume_error<=0;
   if(consume)begin
    if(chunk_ready&&consume_token==tokens[reader])begin
     sealed[reader]<=0;reader<=!reader;
    end else consume_error<=1;
   end
   if(cancel)begin filling<=0;count<=0;end
   else if(seal)begin
    if(filling&&count==wanted)begin
     lengths[writer]<=wanted;tokens[writer]<=pending_token;
     sealed[writer]<=1;writer<=!writer;filling<=0;count<=0;
    end else begin producer_error<=1;filling<=0;count<=0;end
   end else if(begin_valid&&begin_ready)begin
    if(begin_length==0||begin_length>2048)producer_error<=1;
    else begin filling<=1;count<=0;wanted<=begin_length;pending_token<=begin_token;end
   end else if(byte_valid&&byte_ready)count<=count+1'b1;
  end
 end

 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [23:0] address_meta,address_sync;
 reg [23:0] result_address;
 reg [31:0] result_token;
 reg result_valid;
 reg [7:0] result_data;
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin
   address_meta<=0;address_sync<=0;result_address<=0;
   result_token<=0;result_valid<=0;
  end else begin
   address_meta<=address;address_sync<=address_meta;
   result_address<=address_sync;result_token<=tokens[reader];
   result_valid<=chunk_ready&&address_sync[23:11]==13'h801&&
                 {1'b0,address_sync[10:0]}<lengths[reader];
  end
 end
 // 0x400800 >> 11 = 0x801. Keep decode explicit to avoid aliasing 0x400000.
 wire selected=address[23:11]==13'h801;
 always @(posedge clk)result_data<=storage[{reader,address_sync[10:0]}];
 assign data_out=result_data;
 assign dir=enabled&&!read_n&&write_n&&selected;
 assign oe_n=!(dir&&chunk_ready&&result_valid&&result_address==address&&
               result_token==tokens[reader]);
endmodule
