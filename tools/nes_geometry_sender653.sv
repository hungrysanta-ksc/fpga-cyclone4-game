/* Host clock. The canonical little-endian cells are already in the SPI M9K.
 * No wire record is assembled on the normal path. The source RAM remains
 * owned until read and POP, so the fallback can replay every original cell. */
module nes_geometry_sender653(
 input wire clk,reset,run,has_header,input wire [6:0] cells,input wire [12:0] base,
 input wire [15:0] generation,input wire [7:0] q,input wire [15:0] folded,
 output wire [15:0] crc_arg,output wire [7:0] crc_data,
 output reg [9:0] address,output reg write_en,output reg [9:0] write_address,
 output reg [7:0] write_data,output wire done,output reg [8:0] size,output reg [15:0] crc
);
 localparam INIT=0,WAIT_RAM=1,DIGEST=2,SEARCH=3,CMP_A=4,CMP_B=5,CHOOSE=6,
   LITERAL=7,COMMAND=8,STEP=9,HEADER=10,PREFIX=11,FOLD=12,RAW_HEAD=13,
   RAW_GET=14,RAW_BIT=15,FINISHED=16;
 reg [4:0] state,ret;
 reg [7:0] outpos,lit_tag,first,meta;
 reg [6:0] index,lit_count;
 reg [5:0] length,best;
 reg [1:0] lane,best_lane;
 reg half,matched,raw;
 reg [15:0] decoded;
 wire [7:0] prefix=has_header?12:0;
 wire [6:0] distance=lane==0?1:lane==1?2:lane==2?4:33;
 wire [7:0] scan=index+length;
 wire [6:0] ref_index=scan-distance;
 assign done=state==FINISHED;
 assign crc_arg=crc;
 assign crc_data=q;
 task get(input [9:0] a,input [4:0] after_read);
  begin address<=a;ret<=after_read;state<=WAIT_RAM;end
 endtask
 task put(input [7:0] a,input [7:0] b);
  begin write_address<={2'b01,a};write_data<=b;write_en<=1;end
 endtask
 task finish_lane;
  begin
   if(length>best)begin best<=length;best_lane<=lane;end
   length<=0;half<=0;
   if(lane==3)state<=CHOOSE;else begin lane<=lane+1'b1;state<=SEARCH;end
  end
 endtask
 // Original kind-0, four-cell record. The last group is right aligned.
 reg [1:0] slot;
 reg [3:0] cell_bit;
 reg [2:0] filled;
 reg [7:0] bits;
 wire [6:0] left=cells-index;
 wire [2:0] group_size=left>=4?3'd4:left[2:0];
 wire [2:0] padding=3'd4-group_size;
 wire [6:0] raw_index=index+slot-padding;
 wire [12:0] raw_start=base+index;
 wire [7:0] with_bit={bits[6:0],(slot<padding)?1'b0:q[cell_bit[2:0]]};
 always @(posedge clk)begin
  write_en<=0;
  if(reset||!run)state<=INIT;
  else case(state)
   INIT:begin index<=0;half<=0;outpos<=prefix+10;lit_count<=0;matched<=0;raw<=0;
    crc<=16'hffff;get(10'd512,DIGEST);end
   WAIT_RAM:state<=ret;
   DIGEST:begin crc<=folded;half<=!half;
    if(half && index==cells-1'b1)begin decoded<=folded;index<=0;lane<=0;length<=0;best<=0;state<=SEARCH;end
    else if(half)begin index<=index+1'b1;get({2'b10,index+7'd1,1'b0},DIGEST);end
    else get({2'b10,index,1'b1},DIGEST);end
   SEARCH:if(distance>index || scan>=cells || length==32)finish_lane();
    else get({2'b10,scan[6:0],half},CMP_A);
   CMP_A:begin first<=q;get({2'b10,ref_index,half},CMP_B);end
   CMP_B:if(first!=q)finish_lane();
    else begin half<=!half;if(half)length<=length+1'b1;state<=SEARCH;end
   CHOOSE:if(best>=2 || index==cells)begin
     if(lit_count!=0)put(lit_tag,lit_count-1'b1);
     lit_count<=0;state<=COMMAND;
    end else begin
     if(lit_count==0)begin lit_tag<=outpos;outpos<=outpos+1'b1;end
     half<=0;get({2'b10,index,1'b0},LITERAL);end
   LITERAL:begin put(outpos,q);outpos<=outpos+1'b1;
    if(!half)begin half<=1;get({2'b10,index,1'b1},LITERAL);end
    else begin index<=index+1'b1;lit_count<=lit_count+1'b1;state<=STEP;end end
   COMMAND:if(index==cells)begin meta<=0;state<=HEADER;
     if(!matched)begin raw<=1;outpos<=prefix;index<=0;end
    end else begin put(outpos,{1'b1,best_lane,best[4:0]-5'd1});
     matched<=1;outpos<=outpos+1'b1;index<=index+best;state<=STEP;end
   STEP:begin lane<=0;length<=0;best<=0;half<=0;state<=index==cells?CHOOSE:SEARCH;end
   HEADER:if(meta<prefix)get({2'b00,meta},PREFIX);
    else if(raw)begin meta<=0;state<=RAW_HEAD;end
    else begin
     case(meta-prefix)
      0,1:put(meta,8'hff);2:put(meta,generation[15:8]);3:put(meta,generation[7:0]);
      4:put(meta,{3'b0,base[12:8]});5:put(meta,base[7:0]);6:put(meta,0);
      7:put(meta,{1'b0,cells});8:put(meta,decoded[15:8]);9:put(meta,decoded[7:0]);
     endcase
     meta<=meta+1'b1;if(meta==prefix+9)begin
      crc<=16'hffff;meta<=0;get(10'd256,FOLD);end
    end
   PREFIX:begin put(meta,q);meta<=meta+1'b1;state<=HEADER;end
   RAW_HEAD:begin
    case(meta[1:0])
     0:put(outpos,{4'h1,raw_start[11:8]});1:put(outpos,raw_start[7:0]);
     2:put(outpos,generation[15:8]);3:put(outpos,generation[7:0]);
    endcase
    outpos<=outpos+1'b1;meta<=meta+1'b1;
    if(meta[1:0]==3)begin slot<=0;cell_bit<=14;bits<={5'b0,group_size};filled<=4;state<=RAW_GET;end end
   RAW_GET:get({2'b10,raw_index,cell_bit[3]},RAW_BIT);
   RAW_BIT:begin bits<=with_bit;filled<=filled+1'b1;
    if(filled==7)begin put(outpos,with_bit);outpos<=outpos+1'b1;end
    if(cell_bit!=0)begin cell_bit<=cell_bit-1'b1;state<=RAW_GET;end
    else if(slot!=3)begin slot<=slot+1'b1;cell_bit<=14;state<=RAW_GET;end
    else if(index+group_size<cells)begin index<=index+group_size;meta<=0;state<=RAW_HEAD;end
    else begin crc<=16'hffff;meta<=0;get(10'd256,FOLD);end end
   FOLD:begin crc<=folded;
    if(meta==outpos-1'b1)begin size<={1'b0,outpos};state<=FINISHED;end
    else begin meta<=meta+1'b1;get({2'b01,meta+8'd1},FOLD);end end
   FINISHED:state<=FINISHED;
   default:state<=INIT;
  endcase
 end
endmodule
