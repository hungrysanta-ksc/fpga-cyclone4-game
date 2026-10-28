// SPDX-License-Identifier: MIT
// One17bit arithmetic lane replaces the parallel destination/span adders.
// Microprogram bytes are part of the whole synthesis,not a trusted ARM seal.
module nes_check396(input wire clk,reset,start,bank,input wire [95:0] record,
 output reg done,output reg bad);
 wire [15:0] dest=record[15:0],store=record[31:16],decoded=record[47:32],first=record[95:80];
 wire [7:0] flags=record[55:48],wb=record[63:56],vm=record[71:64],region=record[79:72];
 wire ref396=flags[4],stride=flags[5],zero=flags[6];wire [1:0] mode=flags[3:2];
 reg running,step;reg [5:0] pc;reg [16:0] acc;
 (* romstyle="M9K" *) reg [23:0] program396[0:63];reg [23:0] instruction;
 // op:LOAD0,ADD1,SUB2,LTimm3,GTimm4,NEimm5,NEsource6,DONE15,GTsource8.
 task code(input integer at,op,source,input [15:0] immediate);program396[at]={4'(op),4'(source),immediate};endtask
 initial begin
  for(integer i=0;i<64;i++)program396[i]=24'hf00000;
  code(0,0,0,0);code(1,1,6,0);code(2,8,5,0);code(3,0,2,0);code(4,3,0,16'h8000);code(5,1,1,0);code(6,4,0,16'ha000);
  code(7,0,4,0);code(8,1,8,0);code(9,6,3,0);
  code(16,0,0,0);code(17,4,0,2047);code(18,0,2,0);code(19,3,0,16'hc000);code(20,1,1,0);code(21,4,0,16'hd000);
  code(22,0,9,0);code(23,1,6,0);code(24,8,5,0);code(25,0,0,0);code(26,1,8,0);code(27,6,3,0);
  code(32,0,0,0);code(33,1,1,0);code(34,8,5,0);code(35,0,7,0);code(36,1,0,0);code(37,6,2,0);
  code(48,0,0,0);code(49,5,0,0);code(50,0,1,0);code(51,6,5,0);
  code(56,0,0,0);code(57,5,0,21);code(58,0,1,0);code(59,5,0,1100);
 end
 always @(posedge clk)instruction<=program396[pc];
 reg [15:0] source;
 always @*case(instruction[19:16])
  0:source=first;1:source=decoded;2:source=store;3:source=dest;
  4:source=first<<(region==1?4:3);
  5:source=region==0?1024:region==1?128:region==2?(stride?32:2048):region==3?512:region==4?544:3418;
  6:source=decoded>>(region==0?4:region==1?5:1);
  7:source=(region==3?16'h6000:region==4?16'h6200:16'h6500)+(bank?16'h8000:16'd0);
  8:source=region==0?(bank?16'h6000:16'd0):region==1?16'h2000+(bank?16'h2000:16'd0):16'h3000+(bank?16'h2000:16'd0);
  9:source=stride?{11'd0,first[9:5]}:first;
  default:source=0;
 endcase
 wire [3:0] op=instruction[23:20];wire immediate=op>=3&&op<=5;
 wire reverse=op==4||op==8;wire subtract=op==2||op>=3;
 wire [16:0] a=op==0?17'd0:reverse?{1'b0,(immediate?instruction[15:0]:source)}:acc;
 wire [16:0] b=reverse?acc:{1'b0,(immediate?instruction[15:0]:source)};
 wire [17:0] alu={1'b0,a}+{1'b0,(b^{17{subtract}})}+subtract;
 wire wrong=(op==3||op==4||op==8)?!alu[17]:(op==5||op==6)?alu[16:0]!=0:1'b0;
 reg shape;
 always @*begin
  shape=flags[7]||decoded==0||first[15:13]!=0||region>5;
  case(region)
   0,1:shape=shape||flags!=0||decoded>2048||(region==0?decoded[3:0]!=0:decoded[4:0]!=0)||wb!=8'h7e||vm!=8'h80;
   2:shape=shape||ref396||zero||mode!=1||flags[1:0]!=0||decoded[0]||wb!=8'h7e||vm!=(stride?8'h81:8'h80);
   3,4,5:shape=shape||stride||wb!=8'h7f||vm!=0||
    (ref396?(region==5||mode!=0||flags[1:0]!=(region==3?1:2)):(flags[1:0]!=3||mode==0||dest!=0))||
    (zero&&(region!=5||mode!=2));
   default:shape=1;
  endcase
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin running<=0;step<=0;pc<=0;acc<=0;done<=0;bad<=0;end
  else begin
   if(start&&!running)begin bad<=shape;running<=!shape;done<=shape;step<=0;pc<=region<2?0:region==2?16:32;acc<=0;end
   else if(running)begin
    if(!step)step<=1;
    else begin
     step<=0;
     if(op==15||wrong)begin bad<=wrong;done<=1;running<=0;end
     else begin
      if(op<3)acc<=alu[16:0];
      pc<=pc==37?(ref396?48:zero?56:63):pc+1'b1;
     end
    end
   end
  end
 end
endmodule
