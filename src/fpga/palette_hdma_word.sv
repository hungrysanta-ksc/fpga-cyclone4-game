// Experimental G13 direct mode-3 tables. Emit only actual updates and gaps.
// Identical seven-channel ABI/726-byte capacity. Tail after terminator is unused.
// No publish at preclear: caller retains the normal FIFO drain/commit fence.
module palette_hdma_word(
 input wire clk,reset,frame_done,palette_valid,palette_initial,
 input wire[7:0]palette_after_row,input wire[5:0]palette_slot,input wire[14:0]palette_rgb,
 output wire palette_ready,write_valid,input wire write_ready,
 output wire[14:0]write_addr,output wire[15:0]write_data,output reg error,
 input wire preclear);
 localparam IDLE=0,CLEAR=1,INITIAL=2,PREP=3,PATCH=4,APPEND0=5,APPEND1=6,APPEND2=7,FAILED=8,LENGTH=9;
 reg[3:0]state;reg initialized,await_first;
 reg[2:0]channel,phase,event_count,event_index;
 reg[7:0]last_row,target,line_q;
 reg[9:0]last_offset[0:6];reg[7:0]last_line[0:6];reg[5:0]last_slot[0:6];
 reg[9:0]offset_q;reg[5:0]slot_q,old_slot;reg[14:0]rgb_q;
 reg[6:0]gap;reg filler;
 wire[8:0]distance={1'b0,target}-{1'b0,last_line[event_index]};
 wire[14:0]base=15'h4600+event_index*15'h300;
 wire[14:0]clear_base=15'h4600+channel*15'h300;
 assign write_valid=state==CLEAR||state==INITIAL||state==PATCH||state==APPEND0||state==APPEND1||state==APPEND2||state==LENGTH;
 assign write_addr=state==CLEAR?(phase==3?15'h4480+channel*2:clear_base+phase*2):
   state==LENGTH?15'h4480+event_index*2:
   state==INITIAL?15'h4400+{8'b0,palette_slot,1'b0}:
   base+offset_q+(state==PATCH?0:state==APPEND0?5:state==APPEND1?7:9);
 assign write_data=state==CLEAR?(phase==3?16'd6:phase==0?16'd41:16'd0):
   state==LENGTH?{6'b0,offset_q}+16'd11:
   state==INITIAL?{1'b0,palette_rgb}:
   state==PATCH?{2'b0,old_slot,1'b0,gap}:
   state==APPEND0?{2'b0,slot_q,8'd1}:
   state==APPEND1?{rgb_q[7:0],2'b0,slot_q}:{8'd0,1'b0,rgb_q[14:8]};
 assign palette_ready=write_ready&&(state==INITIAL||(state==LENGTH&&!filler));
 integer j;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;initialized<=0;await_first<=1;error<=0;
   channel<=0;phase<=0;event_count<=0;event_index<=0;last_row<=255;
   target<=0;line_q<=0;offset_q<=0;slot_q<=0;old_slot<=0;rgb_q<=0;gap<=0;filler<=0;
   for(j=0;j<7;j=j+1)begin last_offset[j]<=0;last_line[j]<=0;last_slot[j]<=0;end
  end else begin
   if(frame_done)begin initialized<=0;await_first<=1;last_row<=255;event_count<=0;end
   case(state)
    IDLE:if(preclear&&!initialized)begin channel<=0;phase<=0;state<=CLEAR;end
    else if(palette_valid)begin
     if(await_first&&(!palette_initial||palette_slot!=0))begin error<=1;state<=FAILED;end
     else if(!initialized)begin channel<=0;phase<=0;state<=CLEAR;end
     else if(palette_initial)begin await_first<=0;state<=INITIAL;end
     else if(palette_after_row>=143||(last_row!=255&&palette_after_row<last_row)||
             (last_row==palette_after_row&&event_count==7))begin error<=1;state<=FAILED;end
     else begin
      event_index<=last_row==palette_after_row?event_count:0;
      event_count<=last_row==palette_after_row?event_count+1'b1:1;
      last_row<=palette_after_row;target<=8'd41+palette_after_row;state<=PREP;
     end
    end
    CLEAR:if(write_ready)begin
     if(phase==3)begin
      last_offset[channel]<=0;last_line[channel]<=0;last_slot[channel]<=0;
      phase<=0;
      if(channel==6)begin initialized<=1;state<=IDLE;end else channel<=channel+1'b1;
     end else phase<=phase+1'b1;
    end
    INITIAL:if(write_ready)state<=IDLE;
    PREP:begin
     if(distance==0||last_offset[event_index]>715)begin error<=1;state<=FAILED;end
     else begin
      offset_q<=last_offset[event_index];old_slot<=last_slot[event_index];
      filler<=distance>127;gap<=distance>127?7'd127:distance[6:0];
      line_q<=distance>127?last_line[event_index]+8'd127:target;
      slot_q<=distance>127?0:palette_slot;rgb_q<=distance>127?0:palette_rgb;
      state<=PATCH;
     end
    end
    PATCH:if(write_ready)state<=APPEND0;
    APPEND0:if(write_ready)state<=APPEND1;
    APPEND1:if(write_ready)state<=APPEND2;
    APPEND2:if(write_ready)begin
     last_offset[event_index]<=offset_q+5;last_line[event_index]<=line_q;last_slot[event_index]<=slot_q;
     state<=LENGTH;
    end
    LENGTH:if(write_ready)state<=filler?PREP:IDLE;
   endcase
  end
 end
 endmodule
