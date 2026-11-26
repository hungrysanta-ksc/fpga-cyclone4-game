/* Host-clock intervals for one input generation. Diagnostic metadata occupies
 * the seven high bits of response byte 5. D0 remains the length authority. */
module nes_input_times1035(
 input wire clk,reset,phase,source_release,source_start,first_offer,first_read,pop,pop_first,
 output wire [6:0] stamp
);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] rs,cs;
 reg rp,cp,pp;
 always @(posedge clk)begin
  rs<={rs[0],source_release};cs<={cs[0],source_start};
  rp<=rs[1];cp<=cs[1];pp<=phase;
 end
 wire released=rs[1]&&!rp,started=cs[1]&&!cp;
 localparam NONE=0,RELEASED=1,CAPTURING=2,OFFER=3,READ=4;
 reg [2:0] state;
 reg [6:0] age,to_start,to_offer;
 reg [1:0] extra;
 always @(posedge clk)begin
  if(reset)begin
   state<=NONE;age<=0;extra<=0;to_start<=127;to_offer<=127;
  end else begin
   if(released)begin state<=RELEASED;age<=0;to_start<=127;to_offer<=127;end
   else if(started)begin
    to_start<=state==RELEASED?age:7'd127;state<=CAPTURING;age<=0;
   end else if(first_offer && state!=OFFER && state!=READ)begin
    to_offer<=state==CAPTURING?age:7'd127;state<=OFFER;age<=0;
   end else if(first_read && first_offer && state==OFFER)state<=READ;
   else if(phase&&!pp && state!=READ && age!=127)age<=age+1'b1;
   if(pop)begin
    if(pop_first)extra<=1;
    else if(extra==1)extra<=2;
    else extra<=0;
   end
  end
 end
 assign stamp=pop_first?(state==READ?age:7'd127):
              extra==1?to_start:extra==2?to_offer:7'd0;
endmodule
