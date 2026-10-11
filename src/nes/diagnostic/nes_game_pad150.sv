// SPDX-License-Identifier: MIT
// Host snapshot held until acknowledgement; NES shifts only AFTER a read.
module nes_game_pad150(
 input wire host_clk,nes_clk,reset,input wire commit,
 input wire [15:0] snes_buttons,output wire host_ready,
 input wire strobe,read_clock,output wire serial
);
 // Asynchronous assertion, local host-clock release. NES reset is already
 // released by core_release in its own domain at the physical top.
 (* async_reg="true" *) reg [1:0] host_release;
 always @(posedge host_clk or posedge reset)
  if(reset)host_release<=0;else host_release<={host_release[0],1'b1};
 wire host_reset=!host_release[1];

 reg [7:0] held_buttons,current_buttons,shift;
 reg request_toggle,ack_toggle;
 (* async_reg="true" *) reg request_meta,request_sync,ack_meta,ack_sync;
 reg old_read;
 assign host_ready=request_toggle==ack_sync;
 assign serial=strobe?current_buttons[0]:shift[0];
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin held_buttons<=0;request_toggle<=0;ack_meta<=0;ack_sync<=0;end
  else begin
   ack_meta<=ack_toggle;ack_sync<=ack_meta;
   if(commit && host_ready)begin
    held_buttons<={snes_buttons[8],snes_buttons[9],snes_buttons[10],snes_buttons[11],
                   snes_buttons[12],snes_buttons[13],snes_buttons[15],snes_buttons[7]};
    request_toggle<=!request_toggle;
   end
  end
 end
 always @(posedge nes_clk or posedge reset)begin
  if(reset)begin request_meta<=0;request_sync<=0;ack_toggle<=0;current_buttons<=0;shift<=0;old_read<=0;end
  else begin
   request_meta<=request_toggle;request_sync<=request_meta;old_read<=read_clock;
   if(request_sync!=ack_toggle)begin current_buttons<=held_buttons;ack_toggle<=request_sync;end
   if(strobe)shift<=current_buttons;
   else if(old_read && !read_clock)shift<={1'b1,shift[7:1]};
  end
 end
endmodule
