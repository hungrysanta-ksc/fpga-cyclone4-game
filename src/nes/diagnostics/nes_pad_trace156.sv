// SPDX-License-Identifier: MIT
// Completed serial reads only. Observe changed bytes; retain last16 until STOP.
// Source clock throughout; STOP holds contents, FPGA reconfiguration clears.
module nes_pad_trace156(
 input wire clk,reset,active,freeze,event_valid,
 input wire [7:0] buttons,input wire [7:0] command,
 output reg [55:0] page
);
 reg [31:0] ticks;
 (* ramstyle="M9K" *) reg [31:0] entries[0:15];
 reg [31:0] read_data;
 reg [3:0] next_slot;
 reg [4:0] count;
 reg [15:0] total;
 reg [7:0] previous;
 reg seen,stopped,wrapped;
 //256 source-clock timestamp quantum permits one32bit-wide M9K instead of two.
 // Observer waits two source clocks after command retirement before snapshot.
 always @(posedge clk)begin
  read_data<=entries[command[3:0]];
  if(!reset && active && !stopped && event_valid && (!seen || buttons!=previous))
   entries[next_slot]<={ticks[31:8],buttons};
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin ticks<=0;next_slot<=0;count<=0;total<=0;previous<=0;seen<=0;stopped<=0;wrapped<=0;end
  else begin
   if(active && !stopped)begin
    ticks<=ticks+1'b1;if(ticks==32'hffffffff)wrapped<=1;
    if(event_valid && (!seen || buttons!=previous))begin
     next_slot<=next_slot+1'b1;
     if(count<16)count<=count+1'b1;
     if(total!=16'hffff)total<=total+1'b1;
     previous<=buttons;seen<=1;
    end
   end
   if(freeze || (seen && !active))stopped<=1;
  end
 end
 always @* begin
  if(command==8'h76)page={8'hdf,6'd0,wrapped,stopped,total,3'd0,count,4'd0,next_slot,8'd1};
  else if(command[7:4]==4'h8 && (count==16 || {1'b0,command[3:0]}<count))
   page={8'hdf,read_data[7:0],read_data[31:8],8'd0,8'd1};
  else page=0;
 end
endmodule
