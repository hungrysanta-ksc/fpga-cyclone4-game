// SPDX-License-Identifier: MIT
// frame201 query -> canonical5741 geometry bytes, once, under one immutable
// lease. No base/delta RAM here. Unused fields are ZERO, not stale collector RAM.
module nes_source_query235(
 input wire clk,reset,abort_source,start,output wire start_ready,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [2:0] patch_count,input wire [7:0] row_count,object_count,exception_count,
 input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 output wire out_valid,input wire out_ready,output wire [7:0] out_data,
 output reg [12:0] out_offset,output reg done,output reg [3:0] fault
);
 localparam IDLE=0,ASK=1,WAIT_REPLY=2,EMIT=3,TAIL=4;
 reg [2:0] state,section,lane;
 reg [10:0] index,map_count;
 reg [7:0] objects,exceptions;reg [6:0] palettes;reg [2:0] patches;
 reg [15:0] generation;reg [63:0] held;
 reg [10:0] limit,capacity;reg [3:0] width;
 wire lease_ok=frame_owned&&geometry_valid&&frame_generation==generation;
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 assign start_ready=!reset&&!fault&&state==IDLE&&!abort_source;
 assign query=live&&state==ASK&&index<limit;
 assign query_kind=section;assign query_index={2'd0,index};assign query_generation=generation;
 assign out_valid=live&&(state==EMIT||state==TAIL);
 reg [15:0] tail_word;
 always @*begin
  case(section)
   0:begin limit=map_count;capacity=1056;width=2;end
   1:begin limit=224;capacity=224;width=1;end
   2:begin limit={3'd0,objects};capacity=128;width=8;end
   3:begin limit={3'd0,exceptions};capacity=128;width=4;end
   4:begin limit=224;capacity=224;width=8;end
   default:begin limit={4'd0,palettes};capacity=64;width=1;end
  endcase
  case(index[3:1])
   0:tail_word={5'd0,map_count};1,4:tail_word=224;
   2:tail_word={8'd0,objects};3:tail_word={8'd0,exceptions};5:tail_word={9'd0,palettes};default:tail_word=0;
  endcase
 end
 assign out_data=state==TAIL?(index==12?{5'd0,patches}:index[0]?tail_word[15:8]:tail_word[7:0]):held[7:0];
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;section<=0;lane<=0;index<=0;map_count<=0;objects<=0;exceptions<=0;palettes<=0;patches<=0;generation<=0;held<=0;out_offset<=0;done<=0;fault<=0;end
  else begin
   done<=0;
   if(abort_source)fault<=4;
   else if(state!=IDLE&&!lease_ok)fault<=2;
   else if(!fault)case(state)
    IDLE:if(start)begin
     if(!frame_owned||!geometry_valid||row_count!=224||!group_count||group_count>32||object_count>128||exception_count>128||!palette_count||palette_count>2)fault<=1;
     else begin
      generation<=frame_generation;map_count<={group_count,5'd0}+group_count;objects<=object_count;exceptions<=exception_count;
      palettes<=palette_count==1?32:64;patches<=patch_count;section<=0;index<=0;lane<=0;out_offset<=0;state<=ASK;
     end
    end
    ASK:if(index<limit)state<=WAIT_REPLY;else begin held<=0;state<=EMIT;end
    WAIT_REPLY:if(response)begin
     if(!hit||(section==0&&data[63:15]!=0)||(section==1&&data[63:8]!=0)||
        (section==3&&data[63:32]!=0)||(section==4&&data[63:56]!=0)||(section==5&&data[63:6]!=0))fault<=3;
     else begin held<=data;state<=EMIT;end
    end
    EMIT:if(out_ready)begin
     out_offset<=out_offset+1'b1;held<={8'd0,held[63:8]};
     if({1'b0,lane}+1==width)begin
      lane<=0;
      if(index+1==capacity)begin
       index<=0;if(section==5)state<=TAIL;else begin section<=section+1'b1;state<=ASK;end
      end else begin index<=index+1'b1;state<=ASK;end
     end else lane<=lane+1'b1;
    end
    TAIL:if(out_ready)begin
     if(index==12)begin done<=1;state<=IDLE;end
     else begin index<=index+1'b1;out_offset<=out_offset+1'b1;end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
