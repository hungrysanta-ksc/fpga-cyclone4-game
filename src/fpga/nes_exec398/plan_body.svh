// SPDX-License-Identifier: MIT
// Only payload write handshakes and monotone lifetime counters are local.
// E8/E9/EA interpretation belongs to the shared host instruction stream.
 wire raw=reset||stop||!enable;wire local_reset;
 nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw),.reset(local_reset));
 wire[7:0]command=link270[32:25],incoming=link270[24:17];wire[9:0]count=link270[16:7];
 wire live=enable&&!raw&&!local_reset&&!fault&&!source_fault;
 wire[15:0]length=link270[106:91];wire[7:0]number=link270[74:67];
 reg ended,retiring;reg[15:0]ended_generation,accepted;
 wire[31:0]control398=link270[145:114];wire control_write398=control398[24];wire[7:0]control_address398=control398[23:16];wire[7:0]control_data398=control398[15:8];
 reg[7:0]control_q398;
 always @*case(control_address398)
  128:control_q398={fault||source_fault,2'd0,chunk_ready,plan_idle,retiring,ended,live};
  129:control_q398=accepted[7:0];130:control_q398=accepted[15:8];
  131:control_q398=ended_generation[7:0];132:control_q398=ended_generation[15:8];
  default:control_q398=0;
 endcase
 assign plan_length=length[9:0];assign plan_plans=number[4:0];assign plan_crc=link270[90:75];
 assign admit319=live&&!ended&&!retiring&&plan_idle&&accepted!=16'hffff;
 assign selected=!raw&&!SPI_SS&&count!=0&&(command==8'he8||command==8'he9||command==8'hea);assign miso=link270[107];
 assign crc_take270=count==0 ? (incoming==8'he8||incoming==8'he9||incoming==8'hea) : (command==8'hea ? count<=4 : command==8'he9&&(count<=length+5||count<=3));
 assign status270={8'hd7,8'd4,{fault||source_fault,4'd0,retiring,ended,admit319},accepted,136'd0,control_q398};
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin fault<=0;ended<=0;accepted<=0;retiring<=0;retire<=0;ended_generation<=0;plan_write<=0;plan_seal<=0;plan_data<=0;end
  else begin
   plan_write<=0;plan_seal<=0;retire<=0;
   if(source_fault)fault<=1;
   if(end_sealed)begin if(ended||retiring)fault<=1;ended<=1;ended_generation<=end_generation;end
   if(retire_done)begin if(!retiring)fault<=1;else begin ended<=0;accepted<=0;retiring<=0;end end
   if(control_write398&&control_address398==133&&live)case(control_data398)
    1:begin if(ended||retiring||accepted==16'hffff)fault<=1;else begin plan_seal<=1;accepted<=accepted+1'b1;end end
    2:begin if(!ended||retiring||!plan_idle||chunk_ready)fault<=1;else begin retire<=1;retiring<=1;end end
    default:fault<=1;
   endcase
   if(link270[110]&&command==8'he9&&link270[111])begin
    if(link270[113]&&live&&plan_ready)begin plan_write<=1;plan_data<=incoming;end else fault<=1;
   end
  end
 end
endmodule
