// SPDX-License-Identifier: MIT
// Boundary candidate only: source execution still lives on NES clk in338.
// Common reset; soft STOP drains both live mailboxes, never resets one end.
module nes_query355(
 input wire host_clk,nes_clk,reset,stop,begin_frame,
 output wire drained,active,
 input wire req_valid,output wire req_ready,input wire [31:0] req_data,
 output wire rsp_valid,input wire rsp_ready,output wire [64:0] rsp_data,
 output reg query,output reg [31:0] query_data,
 input wire response,response_hit,input wire [63:0] response_data,
 input wire display_phase,plan_zero,plan_step,
 output reg [9:0] plan_cursor,output reg owner_fault
);
 (* async_reg="true" *) reg [1:0] host_release,nes_release;
 always @(posedge host_clk or posedge reset)
  if(reset)host_release<=0;else host_release<={host_release[0],1'b1};
 always @(posedge nes_clk or posedge reset)
  if(reset)nes_release<=0;else nes_release<={nes_release[0],1'b1};
 wire host_reset=!host_release[1],nes_reset=!nes_release[1];
 reg stop_level,busy,stop_applied;
 (* async_reg="true" *) reg [1:0] stop_n,live_h,drain_h;
 wire request_ready,request_valid,request_take;
 wire [31:0] request_data;
 wire reply_ready,reply_valid,reply_take;wire [64:0] reply_data;
 reg [1:0] ns;localparam IDLE=0,WAIT=1,SEND=2;
 reg [64:0] result;
 wire nes_live=!stop_n[1]&&!stop_applied;
 wire port_idle=ns==IDLE&&!request_valid&&reply_ready&&!query;
 wire nes_drained=stop_n[1]&&stop_applied&&ns==IDLE&&reply_ready&&!request_valid;
 assign active=!stop_level&&live_h[1]&&!stop;
 assign req_ready=active&&!busy&&request_ready;
 assign rsp_valid=active&&reply_valid;
 assign rsp_data=reply_data;
 assign reply_take=stop_level||stop||(active&&rsp_ready);
 assign drained=stop_level&&drain_h[1]&&!busy&&request_ready&&!reply_valid;
 assign request_take=ns==IDLE&&reply_ready;
 nes_native_mailbox206 #(.WIDTH(32)) request_box(
  host_clk,nes_clk,reset,req_valid&&active&&!busy,request_ready,req_data,
  request_valid,request_take,request_data);
 nes_native_mailbox206 #(.WIDTH(65)) response_box(
  nes_clk,host_clk,reset,ns==SEND,reply_ready,result,
  reply_valid,reply_take,reply_data);
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin stop_level<=1;busy<=0;live_h<=0;drain_h<=0;end
  else begin
   live_h<={live_h[0],nes_live};drain_h<={drain_h[0],nes_drained};
   if(stop)stop_level<=1;
   else if(begin_frame&&drained)stop_level<=0;
   if(req_valid&&req_ready)busy<=1;
   if(reply_valid&&reply_take)busy<=0;
  end
 end
 always @(posedge nes_clk or posedge nes_reset)begin
  if(nes_reset)begin stop_applied<=1;stop_n<=3;ns<=IDLE;result<=0;query<=0;query_data<=0;plan_cursor<=0;owner_fault<=0;end
  else begin
   stop_n<={stop_n[0],stop_level};stop_applied<=stop_n[1];query<=0;
   if(stop_n[1])begin plan_cursor<=0;owner_fault<=0;end
   else if(display_phase)begin
    if(!port_idle)owner_fault<=1;
    else if(!owner_fault&&plan_zero)plan_cursor<=0;else if(!owner_fault&&plan_step)plan_cursor<=plan_cursor+10'd1;
   end else if(plan_zero||plan_step)owner_fault<=1;
   case(ns)
    IDLE:if(request_valid&&request_take)begin
     if(stop_n[1]||display_phase||owner_fault)begin result<=0;ns<=SEND;if(display_phase&&!stop_n[1])owner_fault<=1;end
     else begin query<=1;query_data<=request_data;ns<=WAIT;end
    end
    WAIT:if(response)begin result<={(response_hit&&!display_phase&&!owner_fault),response_data};ns<=SEND;end
    SEND:if(reply_ready)ns<=IDLE;
    default:ns<=IDLE;
   endcase
  end
 end
endmodule
