// G4 read-only telemetry. Request/ack toggle transfers a held bundle; the
// source cannot replace it until the destination has accepted the old one.
module gbc_diagnostic_snapshot(
 input wire source_clk,bus_clk,reset,
 input wire[31:0] source_data,
 input wire request,
 output reg busy,output reg valid,output reg[31:0] snapshot
);
 reg request_toggle,acknowledge;
 (* async_reg="true" *)reg[1:0] request_sync,ack_sync;
 (* async_reg="true", preserve, dont_merge *)reg[1:0] reset_pipe;
 reg[31:0] held;
 always @(posedge bus_clk or posedge reset)
  if(reset)reset_pipe<=3;else reset_pipe<={reset_pipe[0],1'b0};
 wire bus_reset=reset_pipe[1];
 always @(posedge source_clk or posedge reset)begin
  if(reset)begin request_sync<=0;acknowledge<=0;held<=0;end
  else begin
   request_sync<={request_sync[0],request_toggle};
   if(request_sync[1]!=acknowledge)begin
    held<=source_data;acknowledge<=request_sync[1];
   end
  end
 end
 always @(posedge bus_clk or posedge bus_reset)begin
  if(bus_reset)begin request_toggle<=0;ack_sync<=0;busy<=0;valid<=0;snapshot<=0;end
  else begin
   ack_sync<={ack_sync[0],acknowledge};
   if(busy&&request_toggle==ack_sync[1])begin snapshot<=held;valid<=1;busy<=0;end
   if(request&&!busy)begin request_toggle<=!request_toggle;valid<=0;busy<=1;end
  end
 end
endmodule
