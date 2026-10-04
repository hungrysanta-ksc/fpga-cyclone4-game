// Mode-0 MCU SPI receiver. SS resets framing even when SCK is stopped.
// Each completed byte is held across a toggle synchronizer into clk.
// The paired MCU spaces bytes by 1 us, including reads, so the held byte and
// response are stable well before the following byte. No dummy SCK preamble.
module gbc_spi(
 input wire clk,SCK,MOSI,inout wire MISO,input wire SSEL,
 output reg cmd_ready,param_ready,
 output reg[7:0]cmd_data,param_data,
 output wire endmessage,startmessage,input wire[7:0]input_data,
 output reg[31:0]byte_cnt,output wire[2:0]bit_cnt
);
 initial begin cmd_ready=0;param_ready=0;cmd_data=0;param_data=0;byte_cnt=0;end
 reg[2:0]bits=0;reg first=1;
 reg[7:0]shift=0,held=0;reg held_first=0,byte_toggle=0;
 always @(posedge SCK or posedge SSEL)begin
  if(SSEL)begin bits<=0;first<=1;end
  else begin bits<=bits+1'b1;if(bits==7)first<=0;end
 end
 always @(posedge SCK)if(!SSEL)begin
  shift<={shift[6:0],MOSI};
  if(bits==7)begin held<={shift[6:0],MOSI};held_first<=first;byte_toggle<=!byte_toggle;end
 end
 (* async_reg="true" *)reg[1:0]received=0,ss_sync=3;
 reg seen=0,ss_previous=1;
 assign bit_cnt=bits;
 assign MISO=!SSEL?input_data[7-bits]:1'bz;
 assign startmessage=ss_previous&&!ss_sync[1];
 assign endmessage=!ss_previous&&ss_sync[1];
 always @(posedge clk)begin
  received<={received[0],byte_toggle};ss_sync<={ss_sync[0],SSEL};ss_previous<=ss_sync[1];
  cmd_ready<=0;param_ready<=0;
  if(received[1]!=seen)begin
   seen<=received[1];
   if(held_first)begin cmd_data<=held;cmd_ready<=1;byte_cnt<=1;end
   else begin param_data<=held;param_ready<=1;byte_cnt<=byte_cnt+1'b1;end
  end
 end
endmodule
