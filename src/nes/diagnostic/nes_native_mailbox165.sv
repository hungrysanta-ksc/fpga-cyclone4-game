// SPDX-License-Identifier: MIT
// One held word. Common asynchronous reset, synchronous local release only.
// Both clocks may pause. Independent endpoint resets are NOT supported.
module nes_native_mailbox165 #(parameter WIDTH=96)(
 input wire src_clk,dst_clk,reset,
 input wire src_valid,output wire src_ready,input wire [WIDTH-1:0] src_data,
 output wire dst_valid,input wire dst_ready,output wire [WIDTH-1:0] dst_data
);
 (* async_reg="true" *) reg [1:0] sr,dr,req_sync,ack_sync,up_src,up_dst;
 reg request,acknowledge,capture,valid;reg [WIDTH-1:0] held,received;
 assign src_ready=!reset&&sr[1]&&up_src[1]&&(request==ack_sync[1]);
 assign dst_valid=!reset&&dr[1]&&up_dst[1]&&valid;
 assign dst_data=received;
 always @(posedge src_clk or posedge reset)begin
  if(reset)begin sr<=0;up_src<=0;ack_sync<=0;request<=0;held<=0;end
  else begin
   sr<={sr[0],1'b1};up_src<={up_src[0],dr[1]};ack_sync<={ack_sync[0],acknowledge};
   if(src_valid&&src_ready)begin held<=src_data;request<=~request;end
  end
 end
 always @(posedge dst_clk or posedge reset)begin
  if(reset)begin dr<=0;up_dst<=0;req_sync<=0;acknowledge<=0;capture<=0;valid<=0;received<=0;end
  else begin
   dr<={dr[0],1'b1};up_dst<={up_dst[0],sr[1]};req_sync<={req_sync[0],request};
   if(dr[1]&&up_dst[1])begin
    if(!valid&&!capture&&req_sync[1]!=acknowledge)capture<=1;
    // An extra destination edge after the synchronized control settles.
    if(capture)begin received<=held;valid<=1;capture<=0;end
    if(dst_valid&&dst_ready)begin valid<=0;acknowledge<=req_sync[1];end
   end
  end
 end
endmodule
