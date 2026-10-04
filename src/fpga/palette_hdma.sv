// G13 isolated packed-mode3 candidate. One channel writes slot,slot,lo,hi.
// Six 726-byte tables at 4600+channel*300; initial RGB palette at4400.
module palette_hdma(
 input wire clk,reset,frame_done,palette_valid,palette_initial,
 input wire[7:0]palette_after_row,input wire[5:0]palette_slot,input wire[14:0]palette_rgb,
 output wire palette_ready,write_valid,input wire write_ready,
 output wire[14:0]write_addr,output wire[7:0]write_data,output reg error);
 localparam IDLE=0,CLEAR=1,FIRST=2,SECOND=3,THIRD=4,FOURTH=5,FAILED=6;
 reg[2:0]state,channel,phase,event_count,event_index;
 reg initialized;reg[7:0]record,last_row;reg[9:0]offset;
 wire[14:0]table_base=15'h4600+channel*15'h300;
 wire[14:0]event_addr=15'h4600+event_index*15'h300+({7'b0,palette_after_row}+15'd1)*15'd5+15'd1;
 assign write_valid=state==CLEAR||state==FIRST||state==SECOND||state==THIRD||state==FOURTH;
 assign write_addr=state==CLEAR?table_base+offset:
  palette_initial?15'h4400+{8'b0,palette_slot,1'b0}+(state==SECOND?15'd1:15'd0):
  event_addr+(state==FIRST?15'd0:state==SECOND?15'd1:state==THIRD?15'd2:15'd3);
 assign write_data=state==CLEAR?(record==145||phase!=0?8'd0:record==0?8'd41:8'd1):
  palette_initial?(state==FIRST?palette_rgb[7:0]:{1'b0,palette_rgb[14:8]}):
  (state==FIRST||state==SECOND)?{2'b0,palette_slot}:state==THIRD?palette_rgb[7:0]:{1'b0,palette_rgb[14:8]};
 assign palette_ready=write_ready&&((palette_initial&&state==SECOND)||(!palette_initial&&state==FOURTH));
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;initialized<=0;channel<=0;phase<=0;event_count<=0;event_index<=0;
   record<=0;last_row<=255;offset<=0;error<=0;
  end else begin
   if(frame_done)begin initialized<=0;event_count<=0;last_row<=255;end
   case(state)
    IDLE:if(palette_valid)begin
     if(!initialized)begin
      if(!palette_initial||palette_slot!=0)begin error<=1;state<=FAILED;end
      else begin channel<=0;phase<=0;record<=0;offset<=0;state<=CLEAR;end
     end else if(!palette_initial)begin
      if(palette_after_row>=143||(last_row==palette_after_row&&event_count==6))begin error<=1;state<=FAILED;end
      else begin
       event_index<=last_row==palette_after_row?event_count:3'd0;
       event_count<=last_row==palette_after_row?event_count+1'b1:3'd1;
       last_row<=palette_after_row;state<=FIRST;
      end
     end else state<=FIRST;
    end
    CLEAR:if(write_ready)begin
     if(record==145)begin
      if(channel==5)begin initialized<=1;state<=FIRST;end
      else begin channel<=channel+1'b1;record<=0;phase<=0;offset<=0;end
     end else begin
      offset<=offset+1'b1;
      if(phase==4)begin phase<=0;record<=record+1'b1;end else phase<=phase+1'b1;
     end
    end
    FIRST:if(write_ready)state<=SECOND;
    SECOND:if(write_ready)state<=palette_initial?IDLE:THIRD;
    THIRD:if(write_ready)state<=FOURTH;
    FOURTH:if(write_ready)state<=IDLE;
   endcase
  end
 end
endmodule
