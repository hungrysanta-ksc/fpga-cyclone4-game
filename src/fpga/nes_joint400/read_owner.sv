// SPDX-License-Identifier: MIT
// Exactly one owner of capture -> ended read -> checker event progression.
module nes_read_owner400(input wire clk,reset,stop,active,start,clear,read_n,
 input wire capture,ended,checker_ready,input wire[23:0]address,ended_address,
 input wire[7:0]data,input wire[31:0]token,input wire[11:0]length,
 input wire[15:0]base_position,input wire map_stride,
 output reg[11:0]count,output reg[15:0]position,output reg[7:0]held_data,
 output reg seen,pending,fault,output wire event_valid);
 reg[23:0]held_address;reg[31:0]held_token;
 wire valid_end=active&&pending&&ended_address==held_address&&token==held_token&&
  ended_address==24'h400800+count&&count<length;
 assign event_valid=ended&&valid_end&&checker_ready&&!reset&&!stop&&!fault;
 always @(posedge clk or posedge reset)begin
  if(reset)begin count<=0;position<=0;held_data<=0;held_address<=0;held_token<=0;seen<=0;pending<=0;fault<=0;end
  else if(stop)begin pending<=0;fault<=1;end
  else if(!fault)begin
   if(read_n)seen<=0;
   if(start)begin if(pending)fault<=1;else begin count<=0;position<=base_position;seen<=0;end end
   if(clear)begin if(pending)fault<=1;else count<=0;end
   if(capture)begin
    seen<=1;
    if(!active||pending||address!=24'h400800+count||count>=length)fault<=1;
    else begin pending<=1;held_address<=address;held_token<=token;held_data<=data;end
   end
   if(ended)begin
    if(!valid_end||!checker_ready)fault<=1;
    else begin pending<=0;count<=count+1'b1;position<=position+(map_stride&&position[0]?16'd63:16'd1);end
   end
  end
 end
endmodule
