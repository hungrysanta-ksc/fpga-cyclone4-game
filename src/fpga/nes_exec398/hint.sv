// SPDX-License-Identifier: MIT
// Host interpretation is in the common byte program. The NES side only
// fetches an immutable tag from the existing tile/context RAM and performs
// one addressed ROM request at a time.
module nes_hint361(input wire host_clk,clk,reset,stop,prelease,display_lease,immutable,
 input wire[15:0] generation,input wire[31:0] epoch,serial,input wire[153:0]link,
 output reg[7:0]control_q398,output wire meta_active398,output wire[3:0]meta_at398,input wire[7:0]meta_q398,
 output wire active,request,output wire[21:0]address,input wire ready,response,error,
 output reg fault,output wire busy,output reg finished);
 reg[1:0]pre_sync,display_sync,complete_sync,launch_sync;
 reg used,launch,complete;reg[2:0]pending_count;reg[6:0]last;
 wire owner=(prelease||display_lease)&&immutable;
 wire host_owner=pre_sync[1]&&!display_sync[1]&&immutable;
 wire[31:0]control=link[145:114];wire write398=control[24];wire[7:0]port398=control[23:16],value398=control[15:8];
 assign busy=launch!=complete_sync[1];
 always @*begin
  control_q398=0;
  case(port398)
   160:control_q398={fault,4'd0,used,busy,host_owner&&!busy&&!used&&!fault};
   161:control_q398=generation[7:0];162:control_q398=generation[15:8];
   163,164,165,166:control_q398=epoch>>((port398-163)*8);
   167,168,169,170:control_q398=serial>>((port398-167)*8);
   default:;
  endcase
 end
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin pre_sync<=0;display_sync<=0;complete_sync<=0;used<=0;launch<=0;pending_count<=0;last<=0;fault<=0;end
  else if(stop)begin pre_sync<=0;display_sync<=0;complete_sync<=0;used<=0;launch<=0;pending_count<=0;last<=0;fault<=0;end
  else begin
   pre_sync<={pre_sync[0],prelease};display_sync<={display_sync[0],display_lease};complete_sync<={complete_sync[0],complete};
   if(!pre_sync[1])used<=0;
   if(write398&&port398==174)pending_count<=value398[2:0];
   if(write398&&port398==175)begin
    if(!host_owner||busy||used||fault||pending_count==0||value398!=1)fault<=1;
    else begin launch<=!launch;used<=1;last<={pending_count,4'b0}-1'b1;end
   end
  end
 end
 localparam IDLE=0,LOW_WAIT=1,LOW_CAPTURE=2,HIGH_WAIT=3,HIGH_CAPTURE=4,RUN=5;
 reg[2:0]state;reg[6:0]cursor;reg[12:0]tag;reg pending;
 assign meta_active398=state>=LOW_WAIT&&state<=HIGH_CAPTURE&&!stop&&!fault;
 assign meta_at398={cursor[6:4],state==HIGH_WAIT||state==HIGH_CAPTURE};
 assign active=state==RUN&&owner&&!stop&&!fault;
 assign request=active&&!pending;
 assign address=22'h200000+{5'd0,tag,4'b0}+cursor[3:0];
 always @(posedge clk or posedge reset)begin
  if(reset)begin complete<=0;launch_sync<=0;state<=IDLE;cursor<=0;tag<=0;pending<=0;finished<=0;end
  else if(stop)begin complete<=0;launch_sync<=0;state<=IDLE;cursor<=0;tag<=0;pending<=0;finished<=0;end
  else begin
   launch_sync<={launch_sync[0],launch};finished<=0;
   if(!owner||fault)begin state<=IDLE;pending<=0;complete<=launch_sync[1];end
   else case(state)
    IDLE:if(launch_sync[1]!=complete)begin cursor<=0;pending<=0;state<=LOW_WAIT;end
    LOW_WAIT:state<=LOW_CAPTURE;
    LOW_CAPTURE:begin tag[7:0]<=meta_q398;state<=HIGH_WAIT;end
    HIGH_WAIT:state<=HIGH_CAPTURE;
    HIGH_CAPTURE:begin tag[12:8]<=meta_q398[4:0];state<=RUN;end
    RUN:begin
     if(request&&ready)pending<=1;
     if(pending&&response)begin
      pending<=0;
      if(error||cursor==last)begin state<=IDLE;complete<=launch_sync[1];finished<=!error;end
      else begin cursor<=cursor+1'b1;if(cursor[3:0]==15)state<=LOW_WAIT;end
     end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
