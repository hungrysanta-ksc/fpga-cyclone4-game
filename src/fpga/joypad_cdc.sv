// Bundled-data CDC. The source keeps bits 7:0 stable before changing the
// commit toggle in bit 8. The two-flop toggle synchronizer therefore gives
// the data bus more than two destination clocks to settle before capture.
module joypad_cdc(
 input wire clk,reset,input wire[9:0]source_update,output reg[8:0]joystick
);
 (* async_reg="true" *)reg[1:0]toggle_sync;
 reg seen;
 always @(posedge clk)begin
  if(reset)begin toggle_sync<=0;seen<=0;joystick<=0;end
  else begin
   toggle_sync<={toggle_sync[0],source_update[9]};
   if(toggle_sync[1]!=seen)begin
    joystick<=source_update[8:0];
    seen<=toggle_sync[1];
   end
  end
 end
endmodule
