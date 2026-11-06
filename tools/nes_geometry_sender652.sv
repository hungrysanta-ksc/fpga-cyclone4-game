/* One original packet owns the input M9K from seal through validated D2.
 * Bytes 0..255 are the fallback, 256..511 the trial encoding and 512..767
 * the decoded cells. All accesses use the existing host clock and RAM. */
module nes_geometry_sender652(
 input wire clk,reset,run,input wire [8:0] raw_size,input wire has_header,
 input wire [7:0] q,output reg [9:0] address,output reg write_en,
 output reg [9:0] write_address,output reg [7:0] write_data,
 output wire done,output reg packed_ok,output reg [8:0] size,output reg [15:0] wire_crc
);
 localparam INIT=0,RECORD=1,TAG=2,TAGLO=3,GENHI=4,GENLO=5,VALUE=6,
   LOW=7,HIGH=8,SCAN=9,DIGEST=10,SEARCH=11,CMP_A=12,CMP_B=13,
   STEP=14,CHOOSE=15,LITERAL=16,LITWRITE=17,LITNEXT=18,COMMAND=19,
   HEADER=20,PREFIX=21,FINAL=22,FOLD=23,WAIT_RAM=24,READ_RAM=25,FINISHED=26;
 reg [4:0] state,after_read;
 reg [8:0] pos,outpos;
 reg [7:0] cells,index,raw_byte,meta,lit_count,lit_tag,first;
 reg [7:0] remaining,cell_end;
 reg [3:0] byte_no;
 reg repeat_tag,start_known,half;
 reg [12:0] start_cell;
 reg [15:0] tag,generation,decoded_crc;
 reg [63:0] value;
 reg [1:0] lane,best_lane;
 reg [5:0] length,best;
 wire [5:0] distance=lane==0?1:lane==1?2:lane==2?4:33;
 wire [7:0] next_cell=index+length;
 wire [7:0] unpack_at=cells+remaining-1'b1;
 wire [7:0] prefix=has_header?12:0;
 assign done=state==FINISHED;
 function automatic [15:0] fold(input [15:0] c,input [7:0] b);
   reg [15:0] x;integer i;
   begin x=c^{b,8'd0};for(i=0;i<8;i=i+1)x=x[15]?(x<<1)^16'h1021:x<<1;fold=x;end
 endfunction
 task get(input [9:0] a,input [4:0] nextstate);
  begin address<=a;after_read<=nextstate;state<=WAIT_RAM;end
 endtask
 task put(input [9:0] a,input [7:0] b);
  begin write_address<=a;write_data<=b;write_en<=1;end
 endtask
 task finish_lane;
  begin
   if(length>best)begin best<=length;best_lane<=lane;end
   length<=0;half<=0;
   if(lane==3)state<=CHOOSE;else begin lane<=lane+1'b1;state<=SEARCH;end
  end
 endtask
 always @(posedge clk)begin
  write_en<=0;
  if(reset||!run)begin state<=INIT;packed_ok<=0;end
  else case(state)
   INIT:begin pos<=prefix;cells<=0;start_known<=0;outpos<=prefix+10;
    lit_count<=0;state<=RECORD;decoded_crc<=16'hffff;wire_crc<=16'hffff;end
   WAIT_RAM:state<=READ_RAM;
   READ_RAM:begin raw_byte<=q;state<=after_read;end
   RECORD:if(pos==raw_size)begin
     if(!start_known||cells==0)state<=FINISHED;
     else begin index<=0;half<=0;state<=SCAN;end
    end else get(pos,TAG);
   TAG:begin tag[15:8]<=raw_byte;pos<=pos+1'b1;
    if(raw_byte[7:4]==1||raw_byte==8'hd0)get(pos+1'b1,TAGLO);else state<=FINISHED;end
   TAGLO:begin tag[7:0]<=raw_byte;repeat_tag<=tag[15:8]==8'hd0;pos<=pos+1'b1;
    if(!start_known && tag[15:12]==1)begin start_cell<={tag[11:8],raw_byte}-cells;start_known<=1;end
    get(pos+1'b1,GENHI);end
   GENHI:begin generation[15:8]<=raw_byte;pos<=pos+1'b1;get(pos+1'b1,GENLO);end
   GENLO:begin generation[7:0]<=raw_byte;value<=0;byte_no<=0;pos<=pos+1'b1;get(pos+1'b1,VALUE);end
   VALUE:begin value<={value[55:0],raw_byte};pos<=pos+1'b1;byte_no<=byte_no+1'b1;
    if(byte_no==(repeat_tag?1:7))begin
     cell_end<=cells+(repeat_tag?tag[7:0]+1'b1:{4'd0,value[55:52]});
     remaining<=repeat_tag?tag[7:0]+1'b1:{4'd0,value[55:52]};
     if(repeat_tag?({1'b0,tag[7:0]}+1'b1>128-cells):
         (value[55:52]==0 || value[55:52]>4 || value[55:52]>128-cells))state<=FINISHED;
     else state<=LOW;
    end else get(pos+1'b1,VALUE);
   end
   LOW:begin put({2'b10,unpack_at[6:0],1'b0},value[7:0]);state<=HIGH;end
   HIGH:begin put({2'b10,unpack_at[6:0],1'b1},{1'b0,value[14:8]});
    if(!repeat_tag)value<=value>>15;
    if(remaining==1)begin cells<=cell_end;state<=RECORD;end
    else begin remaining<=remaining-1'b1;state<=LOW;end
   end
   SCAN:get({2'b10,index[6:0],half},DIGEST);
   DIGEST:begin decoded_crc<=fold(decoded_crc,raw_byte);half<=!half;
    if(half)begin index<=index+1'b1;if(index+1'b1==cells)begin
     index<=0;lane<=0;length<=0;best<=0;state<=SEARCH;end else state<=SCAN;end else state<=SCAN;end
   SEARCH:if(distance>index || next_cell>=cells || length==32)finish_lane();
    else get({2'b10,next_cell[6:0],half},CMP_A);
   CMP_A:begin first<=raw_byte;get(10'd512+((next_cell-distance)*2)+half,CMP_B);end
   CMP_B:if(first!=raw_byte)finish_lane();
    else begin half<=!half;if(half)length<=length+1'b1;state<=SEARCH;end
   CHOOSE:if(best>=2 || index==cells)begin
     if(lit_count!=0)put({2'b01,lit_tag},lit_count-1'b1);
     lit_count<=0;state<=COMMAND;
    end else begin
     if(lit_count==0)begin lit_tag<=outpos[7:0];outpos<=outpos+1'b1;end
     half<=0;state<=LITERAL;end
   COMMAND:if(outpos>=raw_size)state<=FINISHED;
    else if(index==cells)begin meta<=0;state<=HEADER;end
    else begin put(10'd256+outpos,{1'b1,best_lane,best[4:0]-5'd1});
     outpos<=outpos+1'b1;index<=index+best;state<=STEP;end
   LITERAL:if(outpos>=raw_size)state<=FINISHED;else get({2'b10,index[6:0],half},LITWRITE);
   LITWRITE:begin put(10'd256+outpos,raw_byte);outpos<=outpos+1'b1;
    if(!half)begin half<=1;state<=LITERAL;end
    else begin lit_count<=lit_count+1'b1;index<=index+1'b1;state<=STEP;end end
   STEP:begin lane<=0;length<=0;best<=0;half<=0;if(index==cells)state<=CHOOSE;else state<=SEARCH;end
   HEADER:if(meta<prefix)get({2'b00,meta},PREFIX);
    else begin
     case(meta-prefix)
      0,1:put(10'd256+meta,8'hff);2:put(10'd256+meta,generation[15:8]);
      3:put(10'd256+meta,generation[7:0]);4:put(10'd256+meta,{3'b0,start_cell[12:8]});
      5:put(10'd256+meta,start_cell[7:0]);6:put(10'd256+meta,0);
      7:put(10'd256+meta,cells);8:put(10'd256+meta,decoded_crc[15:8]);
      9:put(10'd256+meta,decoded_crc[7:0]);
     endcase
     meta<=meta+1'b1;if(meta==prefix+9)begin pos<=0;state<=FINAL;end
    end
   PREFIX:begin put(10'd256+meta,raw_byte);meta<=meta+1'b1;state<=HEADER;end
   FINAL:get(10'd256+pos,FOLD);
   FOLD:begin wire_crc<=fold(wire_crc,raw_byte);pos<=pos+1'b1;
    if(pos+1'b1==outpos)begin size<=outpos;packed_ok<=1;state<=FINISHED;end else state<=FINAL;end
   FINISHED:state<=FINISHED;
   default:state<=FINISHED;
  endcase
 end
endmodule
