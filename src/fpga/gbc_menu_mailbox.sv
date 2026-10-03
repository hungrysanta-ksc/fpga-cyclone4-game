// One outstanding SNES command. Payloads remain held across toggle CDC.
module gbc_menu_mailbox(
 input wire core_clk,bus_clk,reset,
 input wire host_write,input wire[7:0]host_data,output wire[7:0]host_status,
 output wire[7:0]command,input wire reply_write,input wire[7:0]reply_data,
 output reg[7:0]flags
);
 reg request_toggle,acknowledge,pending;
 reg[7:0]request_held,request_core,reply_held,reply_bus;
 (* async_reg="true" *) reg[1:0]request_sync,ack_sync;
 (* async_reg="true",preserve,dont_merge *) reg[1:0]reset_pipe;
 reg busy;
 assign command=pending?request_core:8'b0;
 assign host_status={busy,reply_bus[6:0]};
 always @(posedge bus_clk or posedge reset)
  if(reset)reset_pipe<=3;else reset_pipe<={reset_pipe[0],1'b0};
 wire bus_reset=reset_pipe[1];
 always @(posedge bus_clk or posedge bus_reset)begin
  if(bus_reset)begin request_toggle<=0;request_held<=0;ack_sync<=0;reply_bus<=1;busy<=0;end
  else begin
   ack_sync<={ack_sync[0],acknowledge};
   if(busy&&ack_sync[1]==request_toggle)begin reply_bus<=reply_held;busy<=0;end
   if(host_write&&!busy&&host_data!=0)begin request_held<=host_data;request_toggle<=!request_toggle;busy<=1;end
  end
 end
 always @(posedge core_clk or posedge reset)begin
  if(reset)begin request_sync<=0;acknowledge<=0;pending<=0;request_core<=0;reply_held<=1;flags<=1;end
  else begin
   request_sync<={request_sync[0],request_toggle};
   if(!pending&&request_sync[1]!=acknowledge)begin request_core<=request_held;pending<=1;end
   if(reply_write)begin
    flags<=reply_data;
    if(pending)begin reply_held<=reply_data;acknowledge<=request_sync[1];pending<=0;end
   end
  end
 end
endmodule
