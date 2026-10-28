// SPDX-License-Identifier: MIT
// NES-clock online fetch compaction. No full raw-event buffer, no bus requests.
// Palette/fine-X remain in the separately sealed raster packet. This is NOT
// frame-ready: physical CHR fill and host/SNES admission are still required.
//181 Finalize BG at the completed pixel-row boundary, not the last fetch.
// A bad/missing BG row is replaceable ONLY by a complete raw pixel row.
// Source, extension, object and resource faults remain fatal.
module nes_native_compact181(
 input wire clk,reset,release_scene,begin_scene,end_scene,source_fault,
 input wire event_valid,input wire [63:0] event_data,
 input wire row_commit,row_patched,input wire [7:0] committed_row,
 output wire row_needs_patch,
 input wire query,input wire [1:0] query_kind,input wire [10:0] query_address,
 output reg active,owned,valid,output reg [7:0] errors,
 output reg [7:0] row_count,object_count,exception_count,output reg [5:0] group_count,
 output reg response,hit,output wire [63:0] data
);

 reg begin_scene_pipe402,end_scene_pipe402,event_valid_pipe402,row_commit_pipe402,row_patched_pipe402;
 reg[63:0]event_data_pipe402;reg[7:0]committed_row_pipe402;
 always @(posedge clk)begin
  if(reset||release_scene)begin begin_scene_pipe402<=0;end_scene_pipe402<=0;event_valid_pipe402<=0;row_commit_pipe402<=0;row_patched_pipe402<=0;event_data_pipe402<=0;committed_row_pipe402<=0;end
  else begin begin_scene_pipe402<=begin_scene;end_scene_pipe402<=end_scene;event_valid_pipe402<=event_valid;event_data_pipe402<=event_data;
   row_commit_pipe402<=row_commit;row_patched_pipe402<=row_patched;committed_row_pipe402<=committed_row;end
 end
 // 1056*15 +224*8 +128*64 +128*32 =29920 bits, excluding current-row/rank
 // registers. Real M9K packing, LE cost and timing must be fitted later.
 (* ramstyle="M9K" *) reg [14:0] maps[0:1055];
 (* ramstyle="M9K" *) reg [7:0] rows[0:223];
 (* ramstyle="M9K" *) reg [63:0] objects[0:127];
 (* ramstyle="M9K" *) reg [31:0] exceptions[0:127];
 (* ramstyle="M9K, no_rw_check" *)reg[14:0]previous[0:32];reg[14:0]previous_q402;
 reg [5:0] column,copy_column;reg [10:0] copy_base;
 reg [2:0] row_fine,last_fine;
 reg different,copy_busy,retiring,row_bad,previous_valid;
 wire[14:0]previous_value=previous_q402;
 reg [7:0] exception_base;
 reg [7:0] rank_valid;
 (* ramstyle="M9K, no_rw_check" *)reg[61:0]rank402[0:7];reg[61:0]rank_q402;
 wire[37:0]rank_key402=rank_q402[61:24];wire[7:0]rank_mask402=rank_q402[23:16],rank_row402=rank_q402[15:8];wire[6:0]rank_slot402=rank_q402[7:1];
 wire obj=event_data_pipe402[49];wire [12:0] tile=event_data_pipe402[12:0];
 wire [2:0] fine=event_data_pipe402[15:13],rank=event_data_pipe402[52:50];
 wire [7:0] row=event_data_pipe402[32:25],position=event_data_pipe402[40:33],attribute=event_data_pipe402[48:41];
 wire [14:0] cell_value={attribute[1:0],tile};
 wire [8:0] top={1'b0,row}-{6'd0,(attribute[7]?(3'd7-fine):fine)};
 wire [37:0] key={attribute,position,top,tile};
 wire same_object=rank_valid[rank] && rank_key402==key;
 wire [7:0] mask=(same_object?rank_mask402:8'd0)|(8'd1<<fine);
 wire changed=different || !previous_valid || row_fine==0 || row_fine!=last_fine+3'd1;
 wire [5:0] selected_group=changed?group_count:group_count-6'd1;
 wire accept=active && event_valid_pipe402 && !retiring;
 wire mixed_planes=event_data_pipe402[56];
 wire [2:0] low_fine=mixed_planes?event_data_pipe402[55:53]:fine;
 wire cross_tile=event_data_pipe402[61];
 wire [12:0] low_tile=cross_tile?{event_data_pipe402[60:57],event_data_pipe402[24:16]}:tile;
 wire [12:0] cell_index={5'd0,row}*13'd33+{7'd0,position[5:0]};
 wire invalid_extension=event_data_pipe402[63:62]!=0 ||
   (cross_tile?(!mixed_planes || obj || low_tile==tile):(event_data_pipe402[60:57]!=0)) ||
   (mixed_planes?(obj || (!cross_tile && low_fine==fine)):(event_data_pipe402[55:53]!=0));
 wire starting=begin_scene_pipe402 && !active && !owned && !retiring;
 wire bg_shape402=accept&&!invalid_extension&&row<224&&!obj&&row==row_count&&position<=32&&attribute<=3&&rank==0&&!copy_busy;
 wire previous_write402=bg_shape402&&position==column&&!row_bad;
 wire object_write402=accept&&!invalid_extension&&row<224&&obj&&!(rank_valid[rank]&&row<=rank_row402)&&!(!same_object&&object_count==128);
 wire[61:0]rank_data402={key,mask,row,(same_object?rank_slot402:object_count[6:0]),1'b0};
 // Predict the pending event for the pixel-row verdict, which is consumed
 // on the raw row_commit_pipe402 edge before the pipeline's register updates.
 assign row_needs_patch=row_bad||(bg_shape402&&position!=column)||((previous_write402?column+6'd1:column)!=33);
 wire copy_start402=active&&row_commit_pipe402&&committed_row_pipe402==row_count&&row_count<224&&!copy_busy&&!event_valid_pipe402&&!row_patched_pipe402&&changed&&selected_group<32;
 wire[5:0]previous_read402=row_commit?6'd0:copy_start402?6'd1:copy_busy?(copy_column==32?6'd0:copy_column+1'b1):event_data[38:33];
 always @(posedge clk)begin
  previous_q402<=previous[previous_read402];
  rank_q402<=object_write402&&event_data[52:50]==rank?rank_data402:rank402[event_data[52:50]];
  if(!reset&&!release_scene)begin
   if(previous_write402)previous[column]<=cell_value;
   if(object_write402)rank402[rank]<=rank_data402;
  end
 end
 reg [14:0] map_q;reg [7:0] row_q;reg [63:0] object_q;reg [31:0] exception_q;
 reg [1:0] read_kind;
 always @(posedge clk)begin
  map_q<=maps[query_address];row_q<=rows[query_address[7:0]];
  object_q<=objects[query_address[6:0]];exception_q<=exceptions[query_address[6:0]];
  read_kind<=query_kind;
 end
 assign data=!hit?64'd0:read_kind==0?{49'd0,map_q}:read_kind==1?{56'd0,row_q}:read_kind==2?object_q:{32'd0,exception_q};
 always @(posedge clk)if(!reset&&!release_scene&&(copy_start402||copy_busy))maps[copy_start402?group_count*11'd33:copy_base+copy_column]<=previous_value;
 always @(posedge clk)begin
  response<=0;hit<=0;
  if(reset || release_scene)begin
   active<=0;owned<=0;valid<=0;errors<=0;row_count<=0;group_count<=0;object_count<=0;exception_count<=0;
   column<=0;copy_busy<=0;retiring<=0;different<=0;rank_valid<=0;row_fine<=0;last_fine<=0;
   copy_column<=0;copy_base<=0;row_bad<=0;previous_valid<=0;exception_base<=0;
  end else begin
   if(query && owned)begin
    response<=1;
    if(valid)case(query_kind)
     0:if(query_address<group_count*11'd33)begin hit<=1;end
     1:if(query_address<row_count)begin hit<=1;end
     2:if(query_address<object_count)begin hit<=1;end
     3:if(query_address<exception_count)begin hit<=1;end
    endcase
   end
   if(starting)begin
    active<=1;valid<=0;errors<=0;row_count<=0;group_count<=0;object_count<=0;exception_count<=0;
    column<=0;copy_busy<=0;different<=0;rank_valid<=0;row_fine<=0;last_fine<=0;row_bad<=0;previous_valid<=0;exception_base<=0;
   end
   // A changed row has 33 independent copy clocks before its RAM is reused.
   // Any BG input during copying is rejected instead of stalling the PPU.
   if(copy_busy)begin
    
    if(copy_column==32)copy_busy<=0;else copy_column<=copy_column+1'b1;
   end
   if(accept)begin
    if(invalid_extension || row>=224)errors[0]<=1;
    else if(!obj)begin
     if(row!=row_count || position>32 || attribute>3 || rank!=0 || copy_busy)errors[1]<=1;
     else if(position!=column || row_bad)row_bad<=1;
     else begin

      if(column==0)begin row_fine<=fine;different<=!previous_valid || previous_value!=cell_value;end
      else begin
       different<=different || previous_value!=cell_value;
      end
      // One bounded entry holds both plane rows, also at column0. Ordinary
      // per-cell fineY changes share the same entry with low_fine==fine.
      if((column!=0 && fine!=row_fine) || mixed_planes)begin
       if(exception_count==128)errors[2]<=1;
       else begin exceptions[exception_count[6:0]]<={low_tile,cell_index,fine,low_fine};exception_count<=exception_count+1'b1;end
      end
      column<=column+1'b1;
     end
    end else begin
     if(rank_valid[rank] && row<=rank_row402)errors[4]<=1;
     else if(!same_object && object_count==128)errors[5]<=1;
     else begin
      // Stable evaluation rank is part of the fragment. If a sprite changes
      // rank it becomes another masked fragment, avoiding a global sort graph.
      if(same_object)objects[rank_slot402]<={15'd0,rank,mask,key};
      else begin
       objects[object_count[6:0]]<={15'd0,rank,mask,key};
       object_count<=object_count+1'b1;
      end
      rank_valid[rank]<=1;
     end
    end
   end
   // This pulse comes from the pixel RAM after all256 pixels were accepted.
   // Its row index is checked independently; a synthetic/missing commit fails.
   if(active && row_commit_pipe402)begin
    if(committed_row_pipe402!=row_count || row_count>=224 || copy_busy || event_valid_pipe402)errors[1]<=1;
    else begin
     column<=0;row_bad<=0;different<=0;row_count<=row_count+1'b1;
     previous_valid<=!row_patched_pipe402;last_fine<=row_fine;
     if(row_patched_pipe402)begin
      rows[row_count]<=0; // raster descriptor owns the raw slot, never this map
      exception_count<=exception_base;
     end else begin
      exception_base<=exception_count;
      if(row_needs_patch)errors[1]<=1;
      if(selected_group>=32)errors[3]<=1;
      else begin
       rows[row_count]<={selected_group[4:0],row_fine};
       if(changed)begin
        group_count<=group_count+1'b1;copy_busy<=1;copy_column<=1;
        
        copy_base<=group_count*11'd33;
       end
      end
     end
    end
   end
   if((active || starting) && (end_scene_pipe402 || source_fault))begin
    active<=0;retiring<=1;
    if(source_fault)errors[6]<=1;
    if(row_count!=224 || column!=0 || event_valid_pipe402)errors[7]<=1;
   end
   if(retiring && !copy_busy)begin retiring<=0;owned<=1;valid<=errors==0;end
  end
 end
endmodule
