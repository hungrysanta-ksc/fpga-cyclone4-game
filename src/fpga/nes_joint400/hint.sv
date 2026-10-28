// SPDX-License-Identifier: MIT
// Fixed transaction validation. Only immutable, CRC-sealed tags can launch.
module nes_hint361(input wire host_clk,clk,reset,stop,prelease,display_lease,immutable,
 input wire[15:0]generation,input wire[31:0]epoch,serial,input wire[153:0]link,
 output wire[7:0]control_q398,output wire meta_active398,output wire[3:0]meta_at398,input wire[7:0]meta_q398,
 output reg tag_write400,output reg[3:0]tag_at400,output reg[7:0]tag_data400,input wire tag_ready400,
 output wire active,request,output wire[21:0]address,input wire ready,response,error,
 output reg fault,output wire busy,output reg finished);
 reg[1:0]pre_sync,display_sync,complete_sync,launch_sync;reg used,launch,complete;
 reg[2:0]tags;reg[6:0]last;reg packet_bad,packet_owner;
 wire owner=(prelease||display_lease)&&immutable;
 wire host_owner=pre_sync[1]&&!display_sync[1]&&immutable;
 wire[7:0]command=link[32:25],incoming=link[24:17];wire[9:0]count=link[16:7];
 wire be=link[110],ending=link[109];assign control_q398=0;assign busy=launch!=complete_sync[1];
 reg[7:0]identity_byte;
 always @*case(count)
  2:identity_byte=generation[7:0];3:identity_byte=generation[15:8];
  4,5,6,7:identity_byte=epoch>>((count-4)*8);
  default:identity_byte=serial>>((count-8)*8);
 endcase
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin pre_sync<=0;display_sync<=0;complete_sync<=0;used<=0;launch<=0;tags<=0;last<=0;fault<=0;packet_bad<=0;packet_owner<=0;tag_write400<=0;tag_at400<=0;tag_data400<=0;end
  else if(stop)begin pre_sync<=0;display_sync<=0;complete_sync<=0;used<=0;launch<=0;tags<=0;last<=0;fault<=0;packet_bad<=0;packet_owner<=0;tag_write400<=0;end
  else if(!fault)begin
   pre_sync<={pre_sync[0],prelease};display_sync<={display_sync[0],display_lease};complete_sync<={complete_sync[0],complete};
   if(!pre_sync[1])used<=0;
   if(tag_write400&&tag_ready400)tag_write400<=0;
   if(be&&count==0&&incoming==8'hea)begin packet_bad<=0;packet_owner<=host_owner&&!busy&&!used;end
   if(be&&command==8'hea)begin
    if(count==1)begin tags<=incoming[2:0];if(incoming<1||incoming>7)packet_bad<=1;end
    if(count>=2&&count<12&&incoming!=identity_byte)packet_bad<=1;
    if(count>=12&&count<12+{tags,1'b0})begin
     if(count[0]&&incoming[7:5]!=0)packet_bad<=1;
     if(packet_owner&&!packet_bad)begin
      if(tag_write400&&!tag_ready400)fault<=1;
      else begin tag_write400<=1;tag_at400<=count-12;tag_data400<=incoming;end
     end
    end
   end
   if(ending&&command==8'hea&&count!=7)begin
    if(!packet_owner||packet_bad||tags==0||count!=14+{tags,1'b0}||!link[108]||tag_write400)fault<=1;
    else begin launch<=!launch;used<=1;last<={tags,4'b0}-1'b1;end
   end
  end
 end
 localparam IDLE=0,LOW_WAIT=1,LOW_CAPTURE=2,HIGH_WAIT=3,HIGH_CAPTURE=4,RUN=5;
 reg[2:0]state;reg[6:0]cursor;reg[12:0]tag;reg pending;
 assign meta_active398=state>=LOW_WAIT&&state<=HIGH_CAPTURE&&!stop&&!fault;
 assign meta_at398={cursor[6:4],state==HIGH_WAIT||state==HIGH_CAPTURE};
 assign active=state==RUN&&owner&&!stop&&!fault;assign request=active&&!pending;
 assign address=22'h200000+{5'd0,tag,4'b0}+cursor[3:0];
 always @(posedge clk or posedge reset)begin
  if(reset)begin complete<=0;launch_sync<=0;state<=IDLE;cursor<=0;tag<=0;pending<=0;finished<=0;end
  else if(stop)begin complete<=0;launch_sync<=0;state<=IDLE;cursor<=0;tag<=0;pending<=0;finished<=0;end
  else begin
   launch_sync<={launch_sync[0],launch};finished<=0;
   if(!owner||fault)begin state<=IDLE;pending<=0;complete<=launch_sync[1];end
   else case(state)
    IDLE:if(launch_sync[1]!=complete)begin cursor<=0;pending<=0;state<=LOW_WAIT;end
    LOW_WAIT:state<=LOW_CAPTURE;LOW_CAPTURE:begin tag[7:0]<=meta_q398;state<=HIGH_WAIT;end
    HIGH_WAIT:state<=HIGH_CAPTURE;HIGH_CAPTURE:begin tag[12:8]<=meta_q398[4:0];state<=RUN;end
    RUN:begin
     if(request&&ready)pending<=1;
     if(pending&&response)begin pending<=0;
      if(error||cursor==last)begin state<=IDLE;complete<=launch_sync[1];finished<=!error;end
      else begin cursor<=cursor+1'b1;if(cursor[3:0]==15)state<=LOW_WAIT;end
     end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
