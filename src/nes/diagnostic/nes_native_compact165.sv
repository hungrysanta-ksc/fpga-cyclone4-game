// SPDX-License-Identifier: MIT
// NES-clock online fetch compaction. No full raw-event buffer, no bus requests.
// Palette/fine-X remain in the separately sealed raster packet. This is NOT
// frame-ready: physical CHR fill and host/SNES admission are still required.
module nes_native_compact165(
 input wire clk,reset,release_scene,begin_scene,end_scene,source_fault,
 input wire event_valid,input wire [63:0] event_data,
 input wire query,input wire [1:0] query_kind,input wire [10:0] query_address,
 output reg active,owned,valid,output reg [7:0] errors,
 output reg [7:0] row_count,object_count,exception_count,output reg [5:0] group_count,
 output reg response,hit,output reg [63:0] data
);
 // 1056*15 +224*8 +128*64 +128*17 =28000 bits, excluding current-row/rank
 // registers. Real M9K packing, LE cost and timing must be fitted later.
 (* ramstyle="M9K" *) reg [14:0] maps[0:1055];
 (* ramstyle="M9K" *) reg [7:0] rows[0:223];
 (* ramstyle="M9K" *) reg [63:0] objects[0:127];
 (* ramstyle="M9K" *) reg [16:0] exceptions[0:127];
 reg [14:0] previous[0:32];
 reg [5:0] column,copy_column;reg [10:0] copy_base;
 reg [2:0] row_fine,last_fine;
 reg different,copy_busy,retiring;
 reg [7:0] rank_valid;
 reg [37:0] rank_key[0:7];reg [7:0] rank_mask[0:7],rank_row[0:7];
 reg [6:0] rank_slot[0:7];
 wire obj=event_data[49];wire [12:0] tile=event_data[12:0];
 wire [2:0] fine=event_data[15:13],rank=event_data[52:50];
 wire [7:0] row=event_data[32:25],position=event_data[40:33],attribute=event_data[48:41];
 wire [14:0] cell_value={attribute[1:0],tile};
 wire [8:0] top={1'b0,row}-{6'd0,(attribute[7]?(3'd7-fine):fine)};
 wire [37:0] key={attribute,position,top,tile};
 wire same_object=rank_valid[rank] && rank_key[rank]==key;
 wire [7:0] mask=(same_object?rank_mask[rank]:8'd0)|(8'd1<<fine);
 wire changed=different || previous[32]!=cell_value || row_count==0 || row_fine==0 || row_fine!=last_fine+3'd1;
 wire [5:0] selected_group=changed?group_count:group_count-6'd1;
 wire accept=active && event_valid && !retiring;
 wire starting=begin_scene && !active && !owned && !retiring;
 always @(posedge clk)begin
  response<=0;hit<=0;data<=0;
  if(reset || release_scene)begin
   active<=0;owned<=0;valid<=0;errors<=0;row_count<=0;group_count<=0;object_count<=0;exception_count<=0;
   column<=0;copy_busy<=0;retiring<=0;different<=0;rank_valid<=0;row_fine<=0;last_fine<=0;
   copy_column<=0;copy_base<=0;
  end else begin
   if(query && owned)begin
    response<=1;
    if(valid)case(query_kind)
     0:if(query_address<group_count*11'd33)begin hit<=1;data<={49'd0,maps[query_address]};end
     1:if(query_address<row_count)begin hit<=1;data<={56'd0,rows[query_address[7:0]]};end
     2:if(query_address<object_count)begin hit<=1;data<=objects[query_address[6:0]];end
     3:if(query_address<exception_count)begin hit<=1;data<={47'd0,exceptions[query_address[6:0]]};end
    endcase
   end
   if(starting)begin
    active<=1;valid<=0;errors<=0;row_count<=0;group_count<=0;object_count<=0;exception_count<=0;
    column<=0;copy_busy<=0;different<=0;rank_valid<=0;row_fine<=0;last_fine<=0;
   end
   // A changed row has 33 independent copy clocks before its RAM is reused.
   // Any BG input during copying is rejected instead of stalling the PPU.
   if(copy_busy)begin
    maps[copy_base+copy_column]<=previous[copy_column];
    if(copy_column==32)copy_busy<=0;else copy_column<=copy_column+1'b1;
   end
   if(accept)begin
    if(event_data[63:53]!=0 || row>=224)errors[0]<=1;
    else if(!obj)begin
     if(position!=column || row!=row_count || position>32 || attribute>3 || rank!=0 || copy_busy)errors[1]<=1;
     else begin
      previous[column]<=cell_value;
      if(column==0)begin row_fine<=fine;different<=row_count==0 || previous[0]!=cell_value;end
      else begin
       // SMB3 changes vertical addressing inside its split scanline. Keep
       // only exceptional cells, never flatten them to the row's first fineY.
       if(fine!=row_fine)begin
        if(exception_count==128)errors[2]<=1;
        else begin exceptions[exception_count[6:0]]<={row,position[5:0],fine};exception_count<=exception_count+1'b1;end
       end
       different<=different || previous[column]!=cell_value;
      end
      if(column==32)begin
       column<=0;row_count<=row_count+1'b1;last_fine<=row_fine;
       if(selected_group>=32)errors[3]<=1;
       else begin
        rows[row_count]<={selected_group[4:0],row_fine};
        if(changed)begin
         group_count<=group_count+1'b1;copy_busy<=1;copy_column<=0;
         copy_base<=group_count*11'd33;
        end
       end
      end else column<=column+1'b1;
     end
    end else begin
     if(rank_valid[rank] && row<=rank_row[rank])errors[4]<=1;
     else if(!same_object && object_count==128)errors[5]<=1;
     else begin
      // Stable evaluation rank is part of the fragment. If a sprite changes
      // rank it becomes another masked fragment, avoiding a global sort graph.
      if(same_object)objects[rank_slot[rank]]<={15'd0,rank,mask,key};
      else begin
       objects[object_count[6:0]]<={15'd0,rank,mask,key};
       rank_slot[rank]<=object_count[6:0];object_count<=object_count+1'b1;
      end
      rank_key[rank]<=key;rank_mask[rank]<=mask;rank_row[rank]<=row;rank_valid[rank]<=1;
     end
    end
   end
   if((active || starting) && (end_scene || source_fault))begin
    active<=0;retiring<=1;
    if(source_fault)errors[6]<=1;
    if(row_count!=224 || column!=0 || event_valid)errors[7]<=1;
   end
   if(retiring && !copy_busy)begin retiring<=0;owned<=1;valid<=errors==0;end
  end
 end
endmodule
