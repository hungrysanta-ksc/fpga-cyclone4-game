// SPDX-License-Identifier: MIT
// Complete candidate frame controller. Wide codec operands live only in the
// engine scratch RF. Speculative base is invalid after any terminal failure.
module nes_source_encoder246 #(parameter PROGRAM_FILE="operand246.mem")(
 input wire clk,reset,abort_source,start,output wire start_ready,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [31:0] content_epoch,frame_serial,input wire [2:0] patch_count,
 input wire in_valid,output wire in_ready,input wire [7:0] in_data,input wire [12:0] in_offset,
 output wire raw_query,output wire [12:0] raw_index,input wire raw_response,raw_hit,input wire [63:0] raw_data,
 output wire record_valid,input wire record_ready,output wire [7:0] record_length,output wire record_flush,
 output wire byte_valid,input wire byte_ready,output wire [7:0] byte_data,
 input wire ack_valid,output wire ack_ready,input wire ack_accept,input wire [15:0] ack_generation,
 output reg done,output reg [3:0] fault
);
 `include "nes_operand246_entries.vh"
 typedef enum logic [5:0] {IDLE,KSTART,KWAIT,KDRAIN,FETCH,FSTORE,FSTORE_N,
  PREFIX_REQUEST,PREFIX_PREP,PREFIX_RF,PREFIX_BYTE,DISPATCH,ROW_DECIDE,
  LIT_CALL,LIT_RESULT,FLUSH_RESULT,LIT_AFTER,COLD_AFTER,COLD_DONE,
  MASK_RESULT,GROUP_FINISH,GROUP_OUTPUT,GROUP_RESET,GROUP_RESET_DONE,
  MASK_START,RASTER_BODY,RASTER_FINISH,RAW_NEXT,RAW_ASK,RAW_WAIT,RAW_AFTER,
  RAW_DONE,WAITACK} state_t;
 state_t state;
 typedef enum logic [4:0] {R_INIT,R_DISPATCH,R_ROW,R_TO_DISPATCH,R_LIT,R_FLUSH_LIT,
  R_COLD_APPEND,R_COLD_FLUSH,R_COLD_AT,R_MASK,R_GROUP_FLUSH,R_GROUP_EMIT,
  R_GROUP_RESET,R_MASK_SET,R_FINAL_ROW,R_RAW_BEGIN,R_RAW_APPEND,R_RAW_FLUSH,R_RAW_AT} return_t;
 return_t continuation;
 localparam HEADER=0,GEOMETRY_END=1,RAW_END=2;
 localparam DIRECT=0,MAP=1,RASTER=2;
 reg [1:0] prefix_kind,lit_kind;
 reg [4:0] prefix_i;
 reg [7:0] own_byte,new_byte,old_hold,k_result_hold;
 reg [6:0] row_i;
 reg [12:0] cursor;
 reg [2:0] patches;
 reg [31:0] epoch,base_serial;
 wire [31:0] serial=base_serial+32'd1;
 reg [15:0] generation,checksum;
 reg base_valid,cold,raster_mode,raw_mode,group_active,mask_nonzero,expensive,final_group,retry_literal;
 wire lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 assign start_ready=!reset&&!abort_source&&!fault&&state==IDLE;
 assign in_ready=live&&state==FETCH;
 assign raw_query=live&&state==RAW_ASK;
 assign raw_index=cursor;
 assign ack_ready=live&&state==WAITACK;

 (* ramstyle="M9K" *) reg [7:0] base_lo[0:4095];
 (* ramstyle="M9K" *) reg [7:0] base_hi[0:2047];
 reg [7:0] base_lo_q,base_hi_q;reg base_bank_q;
 wire [7:0] base_q=base_bank_q?base_hi_q:base_lo_q;
 wire collect_row=!cold&&(cursor<2112||(cursor>=3872&&cursor<5664));
 wire payload_ready;
 wire base_we=live&&state==FSTORE&&(!collect_row||payload_ready)&&(cold||base_q!=new_byte);
 always @(posedge clk)begin
  base_bank_q<=cursor[12];base_lo_q<=base_lo[cursor[11:0]];
  if(base_we&&!cursor[12])base_lo[cursor[11:0]]<=new_byte;
 end
 always @(posedge clk)begin
  base_hi_q<=base_hi[cursor[10:0]];
  if(base_we&&cursor[12])base_hi[cursor[10:0]]<=new_byte;
 end

 reg [8:0] kentry;
 reg [15:0] argument0,argument1;
 wire kready,kbusy,kdone;wire [3:0] kfault;
 wire [7:0] kresult,k_length,k_data;
 wire k_record,k_byte;
 reg payload_valid,payload_write,rf_read;
 reg [8:0] payload_address;reg [7:0] payload_data;
 wire payload_read_valid;wire [7:0] payload_q;
 // No second argument snapshot in this controller. The engine snapshots the
 // selected pinned input on its start edge; retry keeps the same input bytes.
 always @*begin
  argument0=0;argument1=0;
  case(kentry)
   OP_INIT:argument0={5'd0,patches,8'd0};
   OP_DISPATCH:begin argument0={3'd0,cursor};argument1=cursor<2112?16'd66:16'd8;end
   OP_DIRECT_LITERAL:begin argument0={new_byte,old_hold};argument1={3'd0,cursor}-16'd1;end
   OP_ROW_LITERAL:begin argument0={9'd0,row_i};argument1={15'd0,raster_mode};end
   OP_RAW_APPEND:argument0={8'd0,new_byte};
   OP_LITERAL_AT:argument0={3'd0,cursor};
   OP_FLUSH:argument1={14'd0,raw_mode,raster_mode};
   OP_SHIFT:argument0=k_result_hold[1]?16'd1:16'd255;
   default:begin end
  endcase
 end
 always @*begin
  payload_valid=0;payload_write=0;payload_address=0;payload_data=0;rf_read=0;
  if(state==FSTORE&&collect_row)begin
   payload_valid=live;payload_write=1;payload_address={2'b0,row_i};payload_data=base_q;
  end else if(state==FSTORE_N)begin
   payload_valid=live;payload_write=1;payload_address=9'd128+row_i;payload_data=new_byte;
  end else if(state==PREFIX_PREP&&prefix_kind==GEOMETRY_END&&prefix_i>=4&&prefix_i<8)begin
   payload_valid=live;payload_address=9'd118+prefix_i;rf_read=1;
  end
 end
 nes_operand246 #(.PROGRAM_FILE(PROGRAM_FILE)) engine(
  .clk(clk),.reset(reset),.abort_source(abort_source||fault!=0),.lease_ok(lease_ok),
  .start(state==KSTART&&kready&&live),.entry(kentry),.argument0(argument0),.argument1(argument1),
  .start_ready(kready),.busy(kbusy),.done(kdone),.fault(kfault),.result(kresult),
  .record_length(k_length),.record_valid(k_record),.record_ready(record_ready&&live),
  .rf_read(rf_read),.payload_valid(payload_valid),.payload_write(payload_write),.payload_address(payload_address),
  .payload_data(payload_data),.payload_ready(payload_ready),.payload_read_valid(payload_read_valid),.payload_q(payload_q),
  .byte_valid(k_byte),.byte_ready(byte_ready&&live),.byte_data(k_data));

 wire [7:0] own_length=prefix_kind==HEADER?8'd20:prefix_kind==GEOMETRY_END?8'd10:8'd6;
 wire own_output=state==PREFIX_REQUEST||state==PREFIX_PREP||state==PREFIX_RF||state==PREFIX_BYTE;
 assign record_valid=live&&(state==PREFIX_REQUEST||k_record);
 assign record_length=own_output?own_length:k_length;
 assign record_flush=state==PREFIX_REQUEST&&prefix_kind==RAW_END;
 assign byte_valid=live&&(state==PREFIX_BYTE||k_byte);
 assign byte_data=state==PREFIX_BYTE?own_byte:k_data;
 wire crc_byte=state==PREFIX_BYTE&&prefix_kind!=HEADER&&{3'd0,prefix_i}>=own_length-8'd2;
 function automatic [15:0] crc16(input [15:0] previous,input [7:0] v);
  reg [15:0] c;integer i;begin c=previous^{v,8'd0};
   for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;
  end
 endfunction
 reg [7:0] prefix_value;
 always @*begin
  prefix_value=0;
  if(prefix_kind==HEADER)case(prefix_i)
   0:prefix_value="N";1:prefix_value="4";2:prefix_value=1;3:prefix_value={7'd0,cold};
   4:prefix_value=epoch[7:0];5:prefix_value=epoch[15:8];6:prefix_value=epoch[23:16];7:prefix_value=epoch[31:24];
   8:prefix_value=base_serial[7:0];9:prefix_value=base_serial[15:8];10:prefix_value=base_serial[23:16];11:prefix_value=base_serial[31:24];
   12:prefix_value=serial[7:0];13:prefix_value=serial[15:8];14:prefix_value=serial[23:16];15:prefix_value=serial[31:24];
   16:prefix_value=generation[7:0];17:prefix_value=generation[15:8];default:prefix_value=0;
  endcase
  else if({3'd0,prefix_i}==own_length-8'd2)prefix_value=checksum[7:0];
  else if({3'd0,prefix_i}==own_length-8'd1)prefix_value=checksum[15:8];
  else case(prefix_i)
   0,1:prefix_value=255;2:prefix_value=0;3:prefix_value=prefix_kind==GEOMETRY_END?8'd3:8'd4;default:prefix_value=0;
  endcase
 end
 task automatic invoke(input [8:0] pc,input return_t next_state);
  begin kentry<=pc;continuation<=next_state;state<=KSTART;end
 endtask
 task automatic prefix(input [1:0] kind);
  begin prefix_kind<=kind;prefix_i<=0;state<=PREFIX_REQUEST;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;continuation<=R_INIT;kentry<=0;fault<=0;done<=0;base_valid<=0;base_serial<=0;epoch<=0;generation<=0;
   prefix_kind<=HEADER;lit_kind<=DIRECT;prefix_i<=0;own_byte<=0;new_byte<=0;old_hold<=0;k_result_hold<=0;
   cursor<=0;row_i<=0;patches<=0;checksum<=16'hffff;cold<=1;raster_mode<=0;raw_mode<=0;
   group_active<=0;mask_nonzero<=0;expensive<=0;final_group<=0;retry_literal<=0;
  end else begin
   done<=0;
   if(!fault)begin
    if(abort_source)begin fault<=4;base_valid<=0;end
    else if(state!=IDLE&&!lease_ok)begin fault<=2;base_valid<=0;end
    else if(kfault)begin fault<=kfault;base_valid<=0;end
    else if(ack_valid&&state!=WAITACK&&state!=IDLE)begin fault<=5;base_valid<=0;end
    else begin
     if(byte_valid&&byte_ready&&!crc_byte)checksum<=crc16(checksum,byte_data);
     case(state)
      IDLE:if(start)begin
       if(!frame_owned||!geometry_valid||frame_serial==0||frame_serial==32'hffffffff||
         (!base_valid&&frame_serial!=1)||(base_valid&&(content_epoch!=epoch||frame_serial!=serial)))begin fault<=1;base_valid<=0;end
       else begin
        epoch<=content_epoch;generation<=frame_generation;patches<=patch_count;cold<=!base_valid;
        cursor<=0;row_i<=0;checksum<=16'hffff;raster_mode<=0;raw_mode<=0;group_active<=0;
        mask_nonzero<=0;expensive<=0;final_group<=0;retry_literal<=0;invoke(OP_INIT,R_INIT);
       end
      end
      KSTART:if(kready)state<=KWAIT;
      KWAIT:if(kdone)begin k_result_hold<=kresult;state<=KDRAIN;end
      KDRAIN:if(kready)case(continuation)
       R_INIT:prefix(HEADER);
       R_DISPATCH:if(cursor==5741)prefix(GEOMETRY_END);else state<=FETCH;
       R_ROW:state<=ROW_DECIDE;
       R_TO_DISPATCH:state<=DISPATCH;
       R_LIT:state<=LIT_RESULT;
       R_FLUSH_LIT:state<=FLUSH_RESULT;
       R_COLD_APPEND:state<=COLD_AFTER;
       R_COLD_FLUSH:state<=COLD_DONE;
       R_COLD_AT:state<=FETCH;
       R_MASK:state<=MASK_RESULT;
       R_GROUP_FLUSH:begin if(k_result_hold==1)expensive<=1;state<=GROUP_OUTPUT;end
       R_GROUP_EMIT:state<=GROUP_RESET;
       R_GROUP_RESET:state<=GROUP_RESET_DONE;
       R_MASK_SET:state<=MASK_START;
       R_FINAL_ROW:state<=GROUP_FINISH;
       R_RAW_BEGIN:state<=RAW_NEXT;
       R_RAW_APPEND:state<=RAW_AFTER;
       R_RAW_FLUSH:state<=RAW_DONE;
       R_RAW_AT:state<=RAW_NEXT;
       default:begin fault<=6;base_valid<=0;end
      endcase
      PREFIX_REQUEST:if(record_ready)state<=PREFIX_PREP;
      PREFIX_PREP:if(prefix_kind==GEOMETRY_END&&prefix_i>=4&&prefix_i<8)begin if(payload_ready)state<=PREFIX_RF;end
       else begin own_byte<=prefix_value;state<=PREFIX_BYTE;end
      PREFIX_RF:if(payload_read_valid)begin own_byte<=payload_q;state<=PREFIX_BYTE;end
      PREFIX_BYTE:if(byte_ready)begin
       if({3'd0,prefix_i}+8'd1==own_length)begin
        if(prefix_kind==HEADER)state<=FETCH;
        else if(prefix_kind==GEOMETRY_END)begin raw_mode<=1;cursor<=0;invoke(OP_RAW_BEGIN,R_RAW_BEGIN);end
        else state<=WAITACK;
       end else begin prefix_i<=prefix_i+1'b1;state<=PREFIX_PREP;end
      end
      FETCH:if(in_valid)begin
       if(in_offset!=cursor||cursor>=5741)begin fault<=3;base_valid<=0;end
       else begin new_byte<=in_data;state<=FSTORE;end
      end
      FSTORE:if(collect_row)begin if(payload_ready)state<=FSTORE_N;end
       else begin
        cursor<=cursor+1'b1;
        if(cold)invoke(OP_RAW_APPEND,R_COLD_APPEND);
        else begin old_hold<=base_q;lit_kind<=DIRECT;invoke(OP_DIRECT_LITERAL,R_LIT);end
       end
      FSTORE_N:if(payload_ready)begin
       cursor<=cursor+1'b1;
       if(row_i==(cursor<2112?7'd65:7'd7))begin
        row_i<=0;
        if(cursor<2112)invoke(OP_ROW_COMPARE,R_ROW);
        else if(group_active)invoke(OP_MASK_COMPARE,R_MASK);else state<=GROUP_FINISH;
       end else begin row_i<=row_i+1'b1;state<=FETCH;end
      end
      COLD_AFTER:if(k_result_hold==240||cursor==5741)invoke(OP_FLUSH,R_COLD_FLUSH);else state<=FETCH;
      COLD_DONE:if(cursor==5741)prefix(GEOMETRY_END);else invoke(OP_LITERAL_AT,R_COLD_AT);
      DISPATCH:begin row_i<=0;invoke(OP_DISPATCH,R_DISPATCH);end
      ROW_DECIDE:if(k_result_hold[0])state<=DISPATCH;
       else if(|k_result_hold[2:1])invoke(OP_SHIFT,R_TO_DISPATCH);
       else begin row_i<=0;lit_kind<=MAP;state<=LIT_CALL;end
      LIT_CALL:if(lit_kind==DIRECT)invoke(OP_DIRECT_LITERAL,R_LIT);else invoke(OP_ROW_LITERAL,R_LIT);
      LIT_RESULT:if(k_result_hold==2||k_result_hold==3)begin retry_literal<=k_result_hold==2;invoke(OP_FLUSH,R_FLUSH_LIT);end
       else begin if(k_result_hold==1)expensive<=1;state<=LIT_AFTER;end
      FLUSH_RESULT:begin
       if(k_result_hold==1)expensive<=1;
       if(retry_literal)state<=LIT_CALL;else state<=LIT_AFTER;
      end
      LIT_AFTER:case(lit_kind)
       DIRECT:if(cursor==3872||cursor==5741)invoke(OP_FLUSH,R_TO_DISPATCH);else state<=FETCH;
       MAP:if(row_i==65)invoke(OP_FLUSH,R_TO_DISPATCH);else begin row_i<=row_i+1'b1;state<=LIT_CALL;end
       RASTER:if(row_i==7||expensive)state<=RASTER_FINISH;else begin row_i<=row_i+1'b1;state<=LIT_CALL;end
       default:begin fault<=6;base_valid<=0;end
      endcase
      MASK_RESULT:if(k_result_hold[0])state<=RASTER_BODY;else state<=GROUP_FINISH;
      GROUP_FINISH:invoke(OP_FLUSH,R_GROUP_FLUSH);
      GROUP_OUTPUT:if(group_active&&mask_nonzero&&expensive)invoke(OP_RASTER,R_GROUP_EMIT);else invoke(OP_CHEAP,R_GROUP_EMIT);
      GROUP_RESET:invoke(OP_GROUP_DONE,R_GROUP_RESET);
      GROUP_RESET_DONE:begin
       group_active<=0;expensive<=0;mask_nonzero<=0;
       if(final_group)begin raster_mode<=0;state<=DISPATCH;end
       else begin raster_mode<=1;invoke(OP_MASK_SET,R_MASK_SET);end
      end
      MASK_START:begin group_active<=1;mask_nonzero<=k_result_hold[0];state<=RASTER_BODY;end
      RASTER_BODY:begin row_i<=0;lit_kind<=RASTER;if(expensive||!mask_nonzero)state<=RASTER_FINISH;else state<=LIT_CALL;end
      RASTER_FINISH:if(cursor==5664)begin final_group<=1;invoke(OP_DISPATCH,R_FINAL_ROW);end else state<=DISPATCH;
      RAW_NEXT:if(cursor=={2'b0,patches,8'b0})prefix(RAW_END);else state<=RAW_ASK;
      RAW_ASK:state<=RAW_WAIT;
      RAW_WAIT:if(raw_response)begin
       if(!raw_hit||raw_data[63:6]!=0)begin fault<=3;base_valid<=0;end
       else begin new_byte<=raw_data[7:0];cursor<=cursor+1'b1;invoke(OP_RAW_APPEND,R_RAW_APPEND);end
      end
      RAW_AFTER:if(k_result_hold==240||cursor=={2'b0,patches,8'b0})invoke(OP_FLUSH,R_RAW_FLUSH);else state<=RAW_NEXT;
      RAW_DONE:invoke(OP_LITERAL_AT,R_RAW_AT);
      WAITACK:if(ack_valid)begin
       if(!ack_accept||ack_generation!=generation)begin fault<=5;base_valid<=0;end
       else begin base_valid<=1;base_serial<=serial;done<=1;state<=IDLE;end
      end
      default:begin fault<=6;base_valid<=0;end
     endcase
    end
   end
  end
 end
endmodule
