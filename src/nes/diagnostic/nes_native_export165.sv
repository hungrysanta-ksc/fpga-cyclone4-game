// SPDX-License-Identifier: MIT
// Native NES-clock lease -> tagged records. Host PREPARED is not DISPLAYED.
// Only COMMIT authorizes the receiver to publish; ABORT discards tentative data.
module nes_native_export165 #(parameter MAX_CYCLES=1048576)(
 input wire clk,reset,enable,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [7:0] row_count,object_count,exception_count,input wire [5:0] group_count,palette_count,
 output reg release_frame,
 output wire query,output reg [2:0] query_kind,output reg [12:0] query_index,
 output wire [15:0] query_generation,input wire response,hit,input wire [63:0] data,
 output wire fill_start,input wire fill_busy,fill_done,fill_success,
 input wire byte_valid,output wire byte_ready,input wire [7:0] byte_data,
 input wire [12:0] byte_tile,input wire [3:0] byte_lane,input wire [1:0] byte_kind,input wire [15:0] byte_generation,
 output reg tx_valid,input wire tx_ready,output reg [95:0] tx_data,
 input wire ack_valid,ack_accept,input wire [15:0] ack_generation,output wire ack_ready,
 output wire busy,output reg [3:0] error
);
 localparam IDLE=0,HEADER=1,ASK=2,REPLY=3,VALUE=4,FSTART=5,FDATA=6,ENDING=7,WAIT_ACK=8,COMMIT=9,ABORT=10,DRAIN=11;
 reg [3:0] state;reg [15:0] generation,records,bytes_count;
 reg [7:0] objects,exceptions;reg [5:0] groups,palettes;reg [63:0] held_data,header;
 reg [31:0] cycles;reg [12:0] limit;
 wire lease_ok=frame_owned&&geometry_valid&&frame_generation==generation;
 wire live=lease_ok&&enable&&cycles<MAX_CYCLES&&!reset;
 assign busy=state!=IDLE;assign query=state==ASK&&query_index<limit&&live;
 assign query_generation=generation;assign fill_start=state==FSTART&&live;
 assign byte_ready=state==FDATA&&live&&tx_ready&&byte_generation==generation;
 assign ack_ready=!reset;
 always @* begin
  case(query_kind)
   0:limit=groups*33;1,4:limit=224;2:limit=objects;3:limit=exceptions;5:limit=palettes*32;default:limit=0;
  endcase
  tx_valid=0;tx_data=0;
  if(live)case(state)
   HEADER:begin tx_valid=1;tx_data={3'd7,generation,13'd0,header};end
   VALUE:begin tx_valid=1;tx_data={query_kind,generation,query_index,held_data};end
   FDATA:if(byte_valid&&byte_generation==generation)begin tx_valid=1;tx_data={3'd6,generation,byte_tile,50'd0,byte_kind,byte_lane,byte_data};end
   ENDING:begin tx_valid=1;tx_data={3'd7,generation,13'd1,32'd0,records,bytes_count};end
  endcase
  if(!reset&&state==COMMIT)begin tx_valid=1;tx_data={3'd7,generation,13'd3,64'd0};end
  if(!reset&&state==ABORT)begin tx_valid=1;tx_data={3'd7,generation,13'd2,60'd0,error};end
 end
 task fail(input [3:0] reason);
  begin error<=reason;state<=ABORT;release_frame<=1;end
 endtask
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;generation<=0;records<=0;bytes_count<=0;objects<=0;exceptions<=0;groups<=0;palettes<=0;
   held_data<=0;header<=0;cycles<=0;query_kind<=0;query_index<=0;release_frame<=0;error<=0;end
  else begin
   release_frame<=0;
   if(state!=IDLE&&state!=ABORT&&state!=DRAIN&&state!=COMMIT)cycles<=cycles+1'b1;
   if(state!=IDLE&&state!=ABORT&&state!=DRAIN&&state!=COMMIT&&!live)fail(1);
   else case(state)
    IDLE:if(enable&&frame_owned)begin
     if(!geometry_valid || row_count!=224 || group_count==0 || group_count>32 || object_count>128 || exception_count>128 || palette_count==0 || palette_count>2)begin release_frame<=1;state<=DRAIN;error<=2;end
     else begin generation<=frame_generation;objects<=object_count;exceptions<=exception_count;groups<=group_count;palettes<=palette_count;
      header<={16'h1651,group_count,palette_count,row_count,object_count,exception_count,12'd0};
      cycles<=0;records<=0;bytes_count<=0;error<=0;query_kind<=0;query_index<=0;state<=HEADER;end
    end
    HEADER:if(tx_ready)state<=ASK;
    ASK:if(query_index>=limit)begin
     query_index<=0;
     if(query_kind==5)state<=FSTART;else query_kind<=query_kind+1'b1;
    end else state<=REPLY;
    REPLY:if(response)begin if(!hit)fail(3);else begin held_data<=data;state<=VALUE;end end
    VALUE:if(tx_ready)begin records<=records+1'b1;query_index<=query_index+1'b1;state<=ASK;end
    FSTART:if(fill_busy)state<=FDATA;else if(fill_done)fail(4);
    FDATA:begin
     if(byte_valid&&byte_generation!=generation)fail(5);
     else if(byte_valid&&byte_ready)begin records<=records+1'b1;bytes_count<=bytes_count+1'b1;end
     if(fill_done)begin if(fill_success)state<=ENDING;else fail(4);end
    end
    ENDING:if(tx_ready)state<=WAIT_ACK;
    WAIT_ACK:if(ack_valid&&ack_generation==generation)begin if(ack_accept)state<=COMMIT;else fail(6);end
    COMMIT:if(tx_ready)begin release_frame<=1;state<=DRAIN;end
    ABORT:if(tx_ready)state<=DRAIN;
    // ABORT may wait while the collector seals the following generation.
    // Do not wait for that NEW lease to disappear without ever serving it.
    DRAIN:if(!fill_busy&&(!frame_owned||frame_generation!=generation))state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
