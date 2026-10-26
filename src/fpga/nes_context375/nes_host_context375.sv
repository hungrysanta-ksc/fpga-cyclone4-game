// SPDX-License-Identifier: MIT
// One host-clock byte sequencer owns queue-header prefetch and cold context
// token checking. DMA uses the already immutable aperture token,not RAM fetch.
module nes_host_context375(input wire clk,reset,active,input wire [7:0] cursor375,
 input wire header_start,input wire [7:0] header_op,queue_data,
 output wire ready,header_busy,header_done,field_valid,output wire [3:0] field_at,output wire [7:0] queue_address,
 input wire put_valid,input wire [5:0] put_address,input wire [7:0] put_data,
 input wire check_start,input wire [31:0] expected_token,
 output wire check_busy,check_done,output reg fault,
 output wire [5:0] ram_address,output wire ram_write,output wire [7:0] ram_data,input wire [7:0] ram_q);
 localparam IDLE=0,HEADER=1,TOKEN=2;
 reg [1:0] mode;wire [7:0] at=cursor375;reg primed;reg [3:0] token_valid;
 wire [1:0] check_lane375=at[1:0]-2'd1;
 wire live=active&&!reset&&!fault;
 wire [4:0] limit=header_op==14?5'd15:header_op==12?5'd14:5'd10;
 assign ready=live&&mode==IDLE;
 assign header_busy=live&&mode==HEADER;
 assign check_busy=live&&mode==TOKEN;
 assign field_valid=header_busy&&primed;
 assign field_at=at[3:0]-1'b1;
 assign queue_address=at<4?at:at+8'd6;
 assign header_done=field_valid&&at==limit;
 assign check_done=check_busy&&primed&&at==4;
 wire field_store=field_valid&&(field_at<2||field_at>=4);
 wire [5:0] field_address=field_at<2?{2'd0,field_at}:{2'd0,field_at}-6'd2;
 assign ram_address=header_busy?field_address:check_busy?6'd8+{4'd0,at[1:0]}:put_address;
 assign ram_write=live&&(field_store||(mode==IDLE&&put_valid&&put_address<52));
 assign ram_data=header_busy?queue_data:put_data;
 always @(posedge clk)begin
  if(reset)begin mode<=IDLE;primed<=0;token_valid<=0;fault<=0;end
  else if(!active)begin mode<=IDLE;primed<=0;token_valid<=0;end
  else if(!fault)begin
   if(header_start&&(!ready||put_valid||check_start))fault<=1;
   if(check_start&&(!ready||put_valid||header_start||token_valid!=15))fault<=1;
   if(put_valid&&(!ready||put_address>=52))fault<=1;
   if(field_store&&field_address>=8&&field_address<=11)token_valid[field_address[1:0]]<=1;
   if(put_valid&&ready&&put_address>=8&&put_address<=11)token_valid[put_address[1:0]]<=1;
   case(mode)
    IDLE:begin
     primed<=0;
     if(header_start&&ready)begin mode<=HEADER;token_valid<=0;end
     else if(check_start&&ready&&token_valid==15)mode<=TOKEN;
    end
    HEADER:begin
     primed<=1;
     if(at==limit)begin mode<=IDLE;primed<=0;end
     else if(at>limit)fault<=1;
     
    end
    TOKEN:begin
     primed<=1;
     if(primed&&ram_q!=expected_token[{check_lane375,3'd0}+:8])fault<=1;
     if(at==4)begin mode<=IDLE;primed<=0;end
     
    end
    default:fault<=1;
   endcase
  end
 end
endmodule
