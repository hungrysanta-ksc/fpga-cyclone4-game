// SPDX-License-Identifier: MIT
// One physical CHR-ROM tile, byte-valid, same source clock. Not a CHR-RAM snapshot.
// Caller flushes on STOP, source write/epoch change, ownership fault and reset.
module nes_chr_cache192(
 input wire clk,reset,flush,request,input wire [31:0] content_epoch,input wire [21:0] address,input wire [15:0] generation,
 output wire ready,idle,response,error,output wire [21:0] response_address,
 output wire [15:0] response_generation,output wire [7:0] data,
 output wire back_request,back_abort,output wire [21:0] back_address,output wire [15:0] back_generation,
 input wire back_ready,back_idle,back_response,back_error,input wire [21:0] back_response_address,
 input wire [15:0] back_response_generation,input wire [7:0] back_data
);
 reg [7:0] bytes[0:15]; // No reset; validity owns exposure.
 reg [15:0] valid;reg [17:0] tag;reg [31:0] cached_epoch;
 reg pending,hit_reply;reg [21:0] held_address;reg [15:0] held_generation;reg [7:0] hit_data;
 wire invalidate=reset||flush||cached_epoch!=content_epoch;
 wire live=!invalidate;
 wire hit=tag==address[21:4]&&valid[address[3:0]];
 assign ready=live&&!pending&&!hit_reply&&(hit||back_ready);
 assign idle=live&&!pending&&!hit_reply&&back_idle;
 assign back_request=request&&ready&&!hit;
 assign back_abort=invalidate;
 assign back_address=address;assign back_generation=generation;
 assign response=live&&(hit_reply||(pending&&back_response));
 assign error=!hit_reply&&back_error;
 assign response_address=hit_reply?held_address:back_response_address;
 assign response_generation=hit_reply?held_generation:back_response_generation;
 assign data=hit_reply?hit_data:back_data;
 always @(posedge clk)begin
  cached_epoch<=content_epoch;
  if(invalidate)begin valid<=0;tag<=0;pending<=0;hit_reply<=0;held_address<=0;held_generation<=0;hit_data<=0;end
  else begin
   hit_reply<=0;
   if(request&&ready)begin
    held_address<=address;held_generation<=generation;
    if(hit)begin hit_reply<=1;hit_data<=bytes[address[3:0]];end
    else pending<=1;
   end
   if(pending&&back_response)begin
    pending<=0;
    if(!back_error&&back_response_address==held_address&&back_response_generation==held_generation)begin
     bytes[held_address[3:0]]<=back_data;
     tag<=held_address[21:4];
     valid<=(tag==held_address[21:4]?valid:16'd0)|(16'd1<<held_address[3:0]);
    end
   end
  end
 end
endmodule
