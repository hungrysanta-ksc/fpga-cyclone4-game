// G13 isolated candidate: seven updates, one shared slot write port.
// Encounter-order IDs, black ID0 pinned. No additional block RAM.
module palette_planner(
 input wire clk_sys,reset,start,input wire[9:0]color_count,
 input wire init_we,input wire[5:0]init_slot,input wire[8:0]init_id,
 output wire req_valid,input wire req_ready,output wire[16:0]req_addr,
 input wire rsp_valid,input wire[7:0]rsp_next,
 output wire update_valid,input wire update_ready,output wire[7:0]update_after_row,
 output wire[5:0]update_slot,output wire[8:0]update_id,
 output reg done,error,output wire busy,output wire[15:0]fault_detail,output wire row_valid,input wire row_ready,output wire[8:0]update_old_id);
 localparam IDLE=0,REQUEST=1,RESPONSE=2,SWAP=3,CHECK=4,FAILED=5,CLEAR_MAP=6;
 reg[2:0]state,swap_index;
 reg[1:0]fault_reason;reg[3:0]fault_flags,missing;
 reg[9:0]count_q;reg[7:0]look_row;reg[8:0]scan_id;
 reg[8:0]clear_index;reg zero_valid;wire[6:0]slot_value;reg[6:0]init_count;reg init_bad;reg[8:0]max_init_id;
 reg[8:0]in_id[0:6],out_id[0:6];reg[8:0]in_time[0:6],out_time[0:6];reg[5:0]out_slot[0:6];
 reg is_resident;reg[5:0]current_slot;reg[2:0]in_rank,out_rank;
 integer k,j;
 wire slots_valid=init_count==64&&!init_bad&&{1'b0,max_init_id}<color_count;
 // Out scores are next-use+1, with zero as the unused sentinel.
 wire[8:0]out_score={1'b0,rsp_next}+9'd1;
 wire swap_valid=in_time[swap_index]<256&&out_time[swap_index]!=0&&
                 ({1'b0,in_time[swap_index]}+10'd1)<{1'b0,out_time[swap_index]};
 assign row_valid=state==CHECK&&missing==0;
 assign fault_detail={look_row,2'b00,fault_reason,fault_flags};
 assign busy=state!=IDLE&&state!=FAILED;
 assign req_valid=state==REQUEST;assign req_addr={look_row,scan_id};
 assign update_valid=state==SWAP&&swap_valid;
 assign update_after_row=look_row-1'b1;
 assign update_old_id=out_id[swap_index];
 assign update_slot=out_slot[swap_index];assign update_id=in_id[swap_index];
 wire response_taken=rsp_valid&&(state==RESPONSE||(state==REQUEST&&req_ready));
 wire[8:0]lookup_address=(state==CHECK&&row_ready)?9'd0:response_taken?scan_id+9'd1:scan_id;
 wire swap_fire=update_valid&&update_ready;
 gbc_inverse_ram resident_ram(clk_sys,swap_fire?update_old_id:lookup_address,swap_fire,7'h40,slot_value,
  state==CLEAR_MAP?clear_index:update_id,state==CLEAR_MAP||swap_fire,
  state==CLEAR_MAP?(({1'b0,clear_index}<count_q&&clear_index<64)?{1'b0,clear_index[5:0]}:7'h40):{1'b0,update_slot});
 always @* begin
  is_resident=!slot_value[6];current_slot=slot_value[5:0];in_rank=7;out_rank=7;
  for(k=6;k>=0;k=k-1)begin
   if({1'b0,rsp_next}<in_time[k])in_rank=k[2:0];
   if(out_score>out_time[k])out_rank=k[2:0];
  end
 end
 always @(posedge clk_sys)begin
  if(reset)begin
   state<=IDLE;swap_index<=0;init_count<=0;init_bad<=0;max_init_id<=0;clear_index<=0;zero_valid<=0;
   done<=0;error<=0;fault_reason<=0;fault_flags<=0;missing<=0;
   count_q<=0;look_row<=0;scan_id<=0;
   for(j=0;j<7;j=j+1)begin in_time[j]<=256;out_time[j]<=0;in_id[j]<=0;out_slot[j]<=0;out_id[j]<=0;end
  end else begin
   done<=0;
   if(init_we&&state==IDLE)begin
    if(init_count>=64||{1'b0,init_slot}!=init_count||init_id!=({4'b0,init_slot}<color_count?{3'b0,init_slot}:9'd0))init_bad<=1;
    if(init_slot==0)zero_valid<=init_id==0;
    if(init_count<64)init_count<=init_count+1'b1;
    if(init_id>max_init_id)max_init_id<=init_id;
   end
   if(start&&state==IDLE)begin
    error<=0;count_q<=color_count;look_row<=0;scan_id<=0;missing<=0;swap_index<=0;
    for(j=0;j<7;j=j+1)begin in_time[j]<=256;out_time[j]<=0;end
    if(!slots_valid||color_count==0||color_count>512||!zero_valid)begin
     error<=1;state<=FAILED;fault_reason<=1;
     fault_flags<={!zero_valid,color_count>512,color_count==0,!slots_valid};
    end else begin clear_index<=0;state<=CLEAR_MAP;end
   end else case(state)
    CLEAR_MAP:if(clear_index==511)state<=REQUEST;else clear_index<=clear_index+1'b1;
    REQUEST,RESPONSE:begin
     if(state==REQUEST&&req_ready&&!rsp_valid)state<=RESPONSE;
     if(rsp_valid&&(state==RESPONSE||req_ready))begin
     if(rsp_next!=255&&(rsp_next<look_row||rsp_next>143))begin
      error<=1;state<=FAILED;fault_reason<=2;
      fault_flags<={2'b00,rsp_next>143,rsp_next<look_row};
     end else begin
      if(!is_resident)begin
       if(rsp_next==look_row&&missing<8)missing<=missing+1'b1;
       for(j=6;j>=0;j=j-1)begin
        if(j==in_rank)begin in_time[j]<={1'b0,rsp_next};in_id[j]<=scan_id;end
        else if(j>in_rank&&j>0)begin in_time[j]<=in_time[j-1];in_id[j]<=in_id[j-1];end
       end
      end else if(scan_id!=0)begin
       for(j=6;j>=0;j=j-1)begin
        if(j==out_rank)begin out_time[j]<=out_score;out_slot[j]<=current_slot;out_id[j]<=scan_id;end
        else if(j>out_rank&&j>0)begin out_time[j]<=out_time[j-1];out_slot[j]<=out_slot[j-1];out_id[j]<=out_id[j-1];end
       end
      end
      if({1'b0,scan_id}+10'd1==count_q)begin swap_index<=0;state<=look_row==0?CHECK:SWAP;end
      else begin scan_id<=scan_id+1'b1;state<=REQUEST;end
     end
    end
    end
    SWAP:begin
     if(!swap_valid)state<=CHECK;
     else if(update_ready)begin
      if(in_time[swap_index]=={1'b0,look_row})missing<=missing-1'b1;
      if(swap_index==6)state<=CHECK;else swap_index<=swap_index+1'b1;
     end
    end
    CHECK:begin
     if(missing!=0)begin error<=1;state<=FAILED;fault_reason<=3;fault_flags<=missing;end
     else if(row_ready)begin
     if(look_row==143)begin done<=1;state<=IDLE;end
     else begin
      look_row<=look_row+1'b1;scan_id<=0;missing<=0;
      for(j=0;j<7;j=j+1)begin in_time[j]<=256;out_time[j]<=0;end
      state<=REQUEST;
     end
     end
    end
   endcase
  end
 end
endmodule
