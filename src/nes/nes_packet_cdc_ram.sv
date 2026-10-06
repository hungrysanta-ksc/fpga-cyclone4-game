// SPDX-License-Identifier: MIT
// One-outstanding bundled-data request/response bridge to the 031 RAM variant of027 queue.
// Common async reset, local synchronous release; independent reset is NOT supported.
module nes_packet_cdc_ram(
 input wire queue_clk,host_clk,reset,
 input wire [15:0] reset_epoch,
 input wire [1:0] p_op,
 input wire [15:0] p_epoch,p_seq,
 input wire [11:0] p_length,
 input wire [7:0] p_data,
 output wire p_accept,
 output wire [3:0] p_error,
 input wire cmd_valid,
 output wire cmd_ready,
 input wire [1:0] cmd_op,
 input wire [15:0] cmd_epoch,cmd_seq,
 input wire [11:0] cmd_address,
 output reg rsp_valid,
 input wire rsp_ready,
 output reg rsp_accept,rsp_data_valid,
 output reg [3:0] rsp_error,
 output reg [7:0] rsp_data,
 output reg [11:0] rsp_length,
 output reg [15:0] rsp_epoch,rsp_seq,
 output reg host_read_owned
);
 (* async_reg="true" *) reg [1:0] q_release,h_release;
 (* async_reg="true" *) reg [1:0] host_up_q,queue_up_h,req_sync,ack_sync;
 wire q_up=q_release[1],h_up=h_release[1];
 reg req_toggle,ack_toggle,pending;
 // Held from request acceptance until response reception. Only synchronized toggle is control.
 reg [1:0] req_op;
 reg [15:0] req_epoch,req_seq;
 reg [11:0] req_address;
 reg [1:0] q_op,phase;
 reg [15:0] q_req_epoch,q_req_seq;
 reg [11:0] q_address,q_saved_length;
 wire q_accept,q_data_valid,q_ready,q_active;
 wire [3:0] q_error,states,raw_p_error;
 wire [7:0] q_data;
 wire [11:0] q_length;
 wire [15:0] q_sequence,q_epoch;
 wire raw_p_accept;
 reg reply_accept,reply_data_valid;
 reg [3:0] reply_error;
 reg [7:0] reply_data;
 reg [11:0] reply_length;
 reg [15:0] reply_epoch,reply_seq;
 assign cmd_ready=!reset && h_up && queue_up_h[1] && !pending && !rsp_valid;
 assign p_accept=!reset && q_up && raw_p_accept;
 assign p_error=(!reset && q_up) ? raw_p_error : 4'd0;
 nes_packet_queue_ram queue(
  .clk(queue_clk),.reset(!q_up),.reset_epoch(reset_epoch),
  .p_op(p_op),.p_epoch(p_epoch),.p_seq(p_seq),.p_length(p_length),.p_data(p_data),
  .p_accept(raw_p_accept),.p_error(raw_p_error),
  .c_op(q_op),.c_epoch(q_req_epoch),.c_seq(q_req_seq),.c_address(q_address),
  .c_accept(q_accept),.c_data_valid(q_data_valid),.c_data(q_data),.c_error(q_error),
  .packet_ready(q_ready),.consumer_active(q_active),.ready_length(q_length),
  .ready_sequence(q_sequence),.epoch(q_epoch),.slot_states(states));
 always @(posedge queue_clk or posedge reset)
  if(reset) q_release<=0; else q_release<={q_release[0],1'b1};
 always @(posedge host_clk or posedge reset)
  if(reset) h_release<=0; else h_release<={h_release[0],1'b1};
 always @(posedge queue_clk or posedge reset) begin
  if(reset) begin
   host_up_q<=0;req_sync<=0;ack_toggle<=0;phase<=0;q_op<=0;
   q_req_epoch<=0;q_req_seq<=0;q_address<=0;q_saved_length<=0;
   reply_accept<=0;reply_error<=0;reply_data_valid<=0;reply_data<=0;
   reply_length<=0;reply_epoch<=0;reply_seq<=0;
  end else begin
   host_up_q<={host_up_q[0],h_up};req_sync<={req_sync[0],req_toggle};q_op<=0;
   if(q_up && host_up_q[1]) case(phase)
    0: if(req_sync[1]!=ack_toggle) begin
       q_op<=req_op;q_req_epoch<=req_epoch;q_req_seq<=req_seq;q_address<=req_address;
       q_saved_length<=q_length;phase<=1;
      end
    1: phase<=2; // queue executes registered command on this edge
    2: begin
       reply_accept<=q_accept;reply_error<=q_error;reply_data_valid<=q_data_valid;reply_data<=q_data;
       reply_length<=q_saved_length;reply_epoch<=q_req_epoch;reply_seq<=q_req_seq;
       ack_toggle<=req_sync[1];phase<=0;
      end
   endcase
  end
 end
 always @(posedge host_clk or posedge reset) begin
  if(reset) begin
   queue_up_h<=0;ack_sync<=0;req_toggle<=0;pending<=0;
   req_op<=0;req_epoch<=0;req_seq<=0;req_address<=0;
   rsp_valid<=0;rsp_accept<=0;rsp_error<=0;rsp_data_valid<=0;rsp_data<=0;
   rsp_length<=0;rsp_epoch<=0;rsp_seq<=0;host_read_owned<=0;
  end else begin
   queue_up_h<={queue_up_h[0],q_up};ack_sync<={ack_sync[0],ack_toggle};
   if(rsp_valid && rsp_ready) rsp_valid<=0;
   if(cmd_valid && cmd_ready) begin
    req_op<=cmd_op;req_epoch<=cmd_epoch;req_seq<=cmd_seq;req_address<=cmd_address;
    req_toggle<=~req_toggle;pending<=1;
   end
   if(h_up && pending && ack_sync[1]==req_toggle) begin
    rsp_accept<=reply_accept;rsp_error<=reply_error;rsp_data_valid<=reply_data_valid;rsp_data<=reply_data;
    rsp_length<=reply_length;rsp_epoch<=reply_epoch;rsp_seq<=reply_seq;rsp_valid<=1;pending<=0;
    if(req_op==1 && reply_accept) host_read_owned<=1;
    if(req_op==3 && reply_accept) host_read_owned<=0;
   end
  end
 end
endmodule
