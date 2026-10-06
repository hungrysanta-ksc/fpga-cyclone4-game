// SPDX-License-Identifier: MIT
// Host-clock packet staging and normalized register/data strobes.
// This is not a physical SNES bus decoder; all host inputs are synchronous.
module nes_host_stage(
 input wire host_clk,reset,
 input wire reg_write,reg_read,
 input wire [3:0] reg_address,
 input wire [7:0] reg_wdata,
 output reg [7:0] reg_rdata,
 output reg reg_rvalid,
 input wire data_read,
 output reg [7:0] data,
 output reg data_valid,
 output wire ready,busy,fault,
 output reg [3:0] bus_error,
 output reg cmd_valid,
 input wire cmd_ready,
 output reg [1:0] cmd_op,
 output reg [15:0] cmd_epoch,cmd_seq,
 output reg [11:0] cmd_address,
 input wire rsp_valid,
 output wire rsp_ready,
 input wire rsp_accept,rsp_data_valid,
 input wire [3:0] rsp_error,
 input wire [7:0] rsp_data,
 input wire [11:0] rsp_length,
 input wire [15:0] rsp_epoch,rsp_seq
);
 localparam IDLE=0,ACQUIRE=1,FILL=2,READY=3,COMMIT=4,FAULT=5;
 reg [2:0] state;
 reg [15:0] epoch_config,seq_config;
 reg [11:0] length,filled,consumed;
 reg waiting;
 reg [7:0] ram[0:3071];
 assign ready=!reset && state==READY;
 assign busy=!reset && state!=IDLE && state!=READY && state!=FAULT;
 assign fault=!reset && state==FAULT;
 assign rsp_ready=!reset && waiting;
 always @(posedge host_clk or posedge reset) begin
  if(reset) begin
   state<=IDLE;epoch_config<=0;seq_config<=0;length<=0;filled<=0;consumed<=0;
   waiting<=0;cmd_valid<=0;cmd_op<=0;cmd_epoch<=0;cmd_seq<=0;cmd_address<=0;
   reg_rdata<=0;reg_rvalid<=0;data<=0;data_valid<=0;bus_error<=0;
  end else begin
   reg_rvalid<=reg_read;data_valid<=0;
   if(reg_read) case(reg_address)
    0:reg_rdata<={5'd0,fault,busy,ready};
    1:reg_rdata<={4'd0,bus_error};
    2:reg_rdata<=epoch_config[7:0];3:reg_rdata<=epoch_config[15:8];
    4:reg_rdata<=seq_config[7:0];5:reg_rdata<=seq_config[15:8];
    6:reg_rdata<=length[7:0];7:reg_rdata<={4'd0,length[11:8]};
    8:reg_rdata<=consumed[7:0];9:reg_rdata<={4'd0,consumed[11:8]};
    default:reg_rdata<=0;
   endcase
   if(reg_write) begin
    if(reg_address==1 && reg_wdata==0) bus_error<=0;
    else if(reg_address>=2 && reg_address<=5) begin
     if(state!=IDLE) bus_error<=1;
     else case(reg_address)
      2:epoch_config[7:0]<=reg_wdata;3:epoch_config[15:8]<=reg_wdata;
      4:seq_config[7:0]<=reg_wdata;5:seq_config[15:8]<=reg_wdata;
     endcase
    end else if(reg_address==0 && reg_wdata==1) begin
     if(state!=IDLE) bus_error<=1;
     else begin
      state<=ACQUIRE;cmd_valid<=1;cmd_op<=1;
      cmd_epoch<=epoch_config;cmd_seq<=seq_config;cmd_address<=0;
      length<=0;filled<=0;consumed<=0;
     end
    end else if(reg_address==0 && reg_wdata==2) begin
     if(state!=READY) bus_error<=7;
     else if(consumed!=length) bus_error<=5;
     else begin state<=COMMIT;cmd_valid<=1;cmd_op<=3;cmd_address<=0;end
    end else bus_error<=8;
   end
   // Accept at most one byte per host edge, after READY. Output is registered.
   if(data_read) begin
    if(state!=READY) bus_error<=7;
    else if(consumed>=length) bus_error<=6;
    else begin data<=ram[consumed];data_valid<=1;consumed<=consumed+1'b1;end
   end
   if(cmd_valid && cmd_ready) begin cmd_valid<=0;waiting<=1;end
   if(rsp_valid && rsp_ready) begin
    waiting<=0;
    if(rsp_epoch!=cmd_epoch || rsp_seq!=cmd_seq) begin state<=FAULT;bus_error<=9;end
    else if(!rsp_accept) begin
     if(state==ACQUIRE && rsp_error==0) state<=IDLE;
     else begin state<=FAULT;bus_error<=rsp_error==0 ? 4'd10 : rsp_error;end
    end else case(state)
     ACQUIRE:begin
      if(rsp_length==0 || rsp_length>3072 || rsp_data_valid) begin state<=FAULT;bus_error<=2;end
      else begin length<=rsp_length;state<=FILL;cmd_valid<=1;cmd_op<=2;cmd_address<=0;end
     end
     FILL:begin
      if(!rsp_data_valid || filled>=length) begin state<=FAULT;bus_error<=10;end
      else begin
       ram[filled]<=rsp_data;filled<=filled+1'b1;
       if(filled+1'b1==length) state<=READY;
       else begin cmd_valid<=1;cmd_address<=filled+1'b1;end
      end
     end
     COMMIT:begin state<=IDLE;length<=0;filled<=0;consumed<=0;end
     default:begin state<=FAULT;bus_error<=10;end
    endcase
   end
  end
 end
endmodule
