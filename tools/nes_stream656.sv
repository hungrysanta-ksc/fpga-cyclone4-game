/* One clock and one input M9K. The walk retains the 655 distance order.
 * A pending literal run is output only once its exclusive end is known.
 * Raw fallback reuses that same sequential byte reader and the host shifter. */
module nes_geometry_sender653 #(parameter INGRESS_CRC=0)(
 input wire clk,reset,run,has_header,input wire [6:0] cells,input wire [12:0] base,
 input wire [15:0] generation,input wire [7:0] q,input wire [15:0] folded,
 input wire cell_write,first_cell,input wire [7:0] input_byte,
 output wire [15:0] crc_arg,output wire [7:0] crc_data,
 input wire serial_busy,output wire raw_load,raw_emit,output wire [14:0] cell_word,
 output wire [12:0] group_start,output wire [2:0] group_count,output reg raw,
 output reg [8:0] address,output reg write_en,output wire [7:0] write_address,
 output reg [7:0] write_data,output wire done,output wire [8:0] size,output reg [15:0] crc
);
 localparam INIT=0,CRC_SCAN=1,HEADER=2,SEARCH=3,CMP_A=4,CMP_B=5,
            CHOOSE=6,STREAM=7,COMMAND=8,STEP=9,RAW_EMIT=10,RAW_WAIT=11,FINISHED=12;
 reg [3:0] state;
 reg wait_read,matched;
 reg [7:0] outpos,first;
 reg [6:0] index,literal_start;
 reg [5:0] length,best;
 reg [1:0] lane,best_lane;
 wire [6:0] distance=lane==0?1:lane==1?2:lane==2?4:33;
 wire [7:0] back={distance,1'b0};
 wire [7:0] delta=state==CMP_A ? -back : state==CMP_B ? back+8'd1 : 8'd1;
 wire [7:0] advanced=address[7:0]+delta;
 wire [7:0] next_cell={1'b0,index}+best;
 wire committing=best>=2 || index==cells;
 wire fallback=index==cells && !matched;
 wire [7:0] prefix=has_header?12:0;
 assign done=state==FINISHED;
 assign size={1'b0,outpos};
 assign crc_arg=INGRESS_CRC && cell_write && first_cell ? 16'hffff : crc;
 assign crc_data=INGRESS_CRC && cell_write ? input_byte : q;
 assign raw_load=run && !wait_read && state==STREAM && raw && address[0];
 assign raw_emit=run && state==RAW_EMIT;
 assign cell_word={q[6:0],first};
 // RAW_EMIT holds the address of the actual final high byte in this group.
 assign group_start=base+{address[7:3],2'b00};
 assign group_count={1'b0,address[2:1]}+3'd1;
 assign write_address=outpos;
 always @* begin
  write_en=run && !reset && !wait_read;write_data=0;
  case(state)
   HEADER:case(index[3:0])
    0,1:write_data=8'hff;2:write_data=generation[15:8];3:write_data=generation[7:0];
    4:write_data={3'b0,base[12:8]};5:write_data=base[7:0];6:write_data=0;
    7:write_data={1'b0,cells};8:write_data=crc[15:8];9:write_data=crc[7:0];
    default:write_en=0;
   endcase
   CHOOSE:begin write_en=write_en && committing && !fallback && literal_start!=index;
    write_data={1'b0,index-literal_start-7'd1};end
   STREAM:begin write_en=write_en && !raw;write_data=q;end
   COMMAND:begin write_en=write_en && index!=cells;
    write_data={1'b1,best_lane,best[4:0]-5'd1};end
   default:write_en=0;
  endcase
 end
 task fetch(input [8:0] where_to,input [3:0] consume);
  begin address<=where_to;state<=consume;wait_read<=1;end
 endtask
 task finish_lane;
  begin
   if(length>best)begin best<=length;best_lane<=lane;end
   length<=0;address<={1'b1,index,1'b0};
   if(lane==3)state<=CHOOSE;else begin lane<=lane+1'b1;state<=SEARCH;end
  end
 endtask
 always @(posedge clk)begin
  if(reset || !run)begin
   state<=INIT;wait_read<=0;
   if(INGRESS_CRC && !reset && cell_write)crc<=folded;
  end else if(wait_read)wait_read<=0;
  else begin
   if(write_en)outpos<=outpos+1'b1;
   case(state)
    INIT:begin index<=0;literal_start<=0;outpos<=prefix;matched<=0;raw<=0;
     if(INGRESS_CRC)state<=HEADER;
     else begin crc<=16'hffff;fetch(9'd256,CRC_SCAN);end end
    CRC_SCAN:begin crc<=folded;
     if(advanced==(address[8]?{cells,1'b0}:outpos))state<=address[8]?HEADER:FINISHED;
     else fetch({address[8],advanced},CRC_SCAN);end
    HEADER:if(index==9)begin index<=0;state<=STEP;end else index<=index+1'b1;
    STEP:begin address<={1'b1,index,1'b0};lane<=0;length<=0;best<=0;
     state<=index==cells?CHOOSE:SEARCH;end
    SEARCH:if(distance>index || address[7:1]==cells || length==32)finish_lane();
     else state<=CMP_A;
    CMP_A:begin first<=q;fetch({1'b1,advanced},CMP_B);end
    CMP_B:if(first!=q)finish_lane();else begin
     if(address[0])length<=length+1'b1;address<={1'b1,advanced};state<=SEARCH;end
    CHOOSE:if(!committing)begin index<=index+1'b1;state<=STEP;end
     else if(fallback)begin raw<=1;fetch(9'd256,STREAM);end
     else if(literal_start!=index)fetch({1'b1,literal_start,1'b0},STREAM);
     else state<=COMMAND;
    STREAM:if(raw)begin
      if(!address[0])first<=q;
      if(address[0] && (address[2:1]==3 || advanced=={cells,1'b0}))state<=RAW_EMIT;
      else fetch({1'b1,advanced},STREAM);
     end else if(advanced=={index,1'b0})state<=COMMAND;
     else fetch({1'b1,advanced},STREAM);
    COMMAND:if(index==cells)begin crc<=16'hffff;fetch(9'd0,CRC_SCAN);end
     else begin matched<=1;index<=next_cell[6:0];literal_start<=next_cell[6:0];state<=STEP;end
    RAW_EMIT:state<=RAW_WAIT;
    RAW_WAIT:if(!serial_busy)begin
     if(advanced=={cells,1'b0})state<=FINISHED;
     else fetch({1'b1,advanced},STREAM);end
    FINISHED:state<=FINISHED;
    default:state<=INIT;
   endcase
  end
 end
endmodule
