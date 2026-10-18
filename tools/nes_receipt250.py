# SPDX-License-Identifier: MIT
"""Single-clock receipt/validity core; packet parsing/CRC/CDC are excluded."""
RTL=r'''
module nes_receipt250(
 input wire clk,reset,abort_source,
 input wire begin_valid,target_bank,input wire [2:0] raw_count,
 input wire range_valid,map_range,input wire [11:0] first,count,
 input wire check_valid,input wire [7:0] check_value,
 input wire finish_valid,all_consumed,display_ack,
 output wire ready,output reg sealed,output reg [3:0] fault
);
 localparam CLEARALL=0,IDLE=1,CLEARFRAME=2,ACTIVE=3,RREAD=4,RWRITE=5,VREAD=6,VWRITE=7,
 CHECKREAD=8,CHECKTEST=9,CHECKVALIDREAD=10,CHECKVALIDTEST=11,WAITDISPLAY=12,RAWINVALID=13;
 reg [3:0] state;reg bank,mapmode;reg [2:0] raw;
 reg [9:0] cursor,check_index,addr;reg [7:0] q,wdata,mask,value;
 reg [11:0] bit_at,left,map_end;reg [3:0] take;reg [1:0] initialized;
 reg we;wire live=!reset&&!abort_source&&!fault;
 (* ramstyle="M9K" *) reg [7:0] memory[0:1023];
 always @(posedge clk)begin q<=memory[addr];if(we)memory[addr]<=wdata;end
 wire [9:0] validbase=bank?10'd166:10'd0;
 wire [3:0] available=8-{1'b0,bit_at[2:0]};
 wire [3:0] ntake=left<available?left[3:0]:available;
 wire [8:0] lowmask=(9'd1<<ntake)-1'b1;
 wire [7:0] nextmask=lowmask[7:0]<<bit_at[2:0];
 assign ready=live&&(state==IDLE||state==ACTIVE);
 always @*begin
  addr=0;we=0;wdata=0;
  case(state)
   CLEARALL:begin addr=cursor;we=1;end
   CLEARFRAME:begin addr=cursor;we=1;end
   RAWINVALID:begin addr=cursor;we=1;end
   RREAD,RWRITE:begin addr=(mapmode?10'd498:10'd332)+{1'b0,bit_at[11:3]};we=state==RWRITE&&(q&mask)==0;wdata=q|mask;end
   VREAD,VWRITE:begin addr=validbase+{1'b0,bit_at[11:3]};we=state==VWRITE;wdata=q|mask;end
   CHECKREAD,CHECKTEST:addr=check_index<144?validbase+check_index:check_index<166?10'd332+check_index:10'd498+check_index-10'd166;
   CHECKVALIDREAD,CHECKVALIDTEST:addr=validbase+check_index;
   default:begin end
  endcase
  if(!live)we=0;
 end
 task advance_range;
  begin if(left==take)state<=ACTIVE;else begin bit_at<=bit_at+take;left<=left-take;state<=RREAD;end end
 endtask
 task advance_check;
  begin check_index<=check_index+1'b1;state<=ACTIVE;end
 endtask
 always @(posedge clk)begin
  if(reset)begin state<=CLEARALL;cursor<=0;check_index<=0;bank<=0;raw<=0;mapmode<=0;bit_at<=0;left<=0;map_end<=0;take<=0;mask<=0;value<=0;initialized<=0;sealed<=0;fault<=0;end
  else if(abort_source)begin fault<=4;sealed<=0;initialized<=0;end
  else if(!fault)begin
   if(display_ack&&state!=WAITDISPLAY)begin fault<=5;sealed<=0;initialized<=0;end
   else case(state)
    CLEARALL:if(cursor==753)state<=IDLE;else cursor<=cursor+1'b1;
    IDLE:if(begin_valid)begin bank<=target_bank;raw<=raw_count;cursor<=332;check_index<=0;map_end<=0;sealed<=0;state<=CLEARFRAME;end
    CLEARFRAME:if(cursor==753)begin if(raw==0)begin cursor<=148;state<=RAWINVALID;end else state<=ACTIVE;end else cursor<=cursor+1'b1;
    RAWINVALID:if(cursor==165)cursor<=314;else if(cursor==331)state<=ACTIVE;else cursor<=cursor+1'b1;
    ACTIVE:begin
     if(begin_valid)fault<=1;
     else if(range_valid)begin
      if(check_index!=0||!count||{1'b0,first}+{1'b0,count}>(map_range?13'd2048:13'd1328)||(map_range&&(first<map_end||count>32)))fault<=2;
      else begin bit_at<=first;left<=count;mapmode<=map_range;if(map_range)map_end<=first+count;state<=RREAD;end
     end else if(check_valid)begin
      if(check_index>=422)fault<=3;else begin value<=check_value;state<=CHECKREAD;end
     end else if(finish_valid)begin
      if(check_index!=422||!all_consumed)fault<=3;else begin sealed<=1;state<=WAITDISPLAY;end
     end
    end
    RREAD:begin mask<=nextmask;take<=ntake;state<=RWRITE;end
    RWRITE:if(q&mask)fault<=2;else if(mapmode)advance_range();else state<=VREAD;
    VREAD:state<=VWRITE;
    VWRITE:advance_range();
    CHECKREAD:state<=CHECKTEST;
    CHECKTEST:begin
     if(check_index<144)begin if(value&~q)fault<=3;else advance_check();end
     else if(check_index<166)begin
      if(raw==0&&check_index>=148)advance_check();else if(q!=value)fault<=3;else state<=CHECKVALIDREAD;
     end else if(q!=value||(!initialized[bank]&&q!=255))fault<=3;else advance_check();
    end
    CHECKVALIDREAD:state<=CHECKVALIDTEST;
    CHECKVALIDTEST:if(q!=255)fault<=3;else advance_check();
    WAITDISPLAY:if(display_ack)begin initialized[bank]<=1;sealed<=0;state<=IDLE;end
    default:fault<=6;
   endcase
  end
 end
endmodule
'''
