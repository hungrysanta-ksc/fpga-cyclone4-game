// SPDX-License-Identifier: MIT
// Passive last16 NES-clock samples, including the first fault edge.
// No clock/control/ROM decisions depend on these outputs. STOP retains RAM.
module nes_ppu_history157(
 input wire clk,reset,active,freeze,
 input wire [95:0] sample,input wire [7:0] command,
 output reg [55:0] page
);
 (* ramstyle="M9K" *) reg [95:0] entries[0:15];
 reg [95:0] read_data;
 reg [3:0] next_slot;
 reg [4:0] count;
 reg stopped,fault_seen;
 always @(posedge clk)begin
  read_data<=entries[command[4:1]];
  if(!reset && active && !stopped)entries[next_slot]<=sample;
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin next_slot<=0;count<=0;stopped<=0;fault_seen<=0;end
  else begin
   if(active && !stopped)begin
    next_slot<=next_slot+1'b1;
    if(count<16)count<=count+1'b1;
   end
   if(!stopped && freeze)begin stopped<=1;fault_seen<=1;end
   else if(count!=0 && !active)stopped<=1;
  end
 end
 always @* begin
  if(command==8'h77)page={8'he0,6'd0,fault_seen,stopped,3'd0,count,4'd0,next_slot,8'd1,8'd96,8'd1};
  else if(command[7:5]==3'b101 && (count==16 || {1'b0,command[4:1]}<count))
   page={8'he0,command[0]?read_data[47:0]:read_data[95:48]};
  else page=0;
 end
endmodule
