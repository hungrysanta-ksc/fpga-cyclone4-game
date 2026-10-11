// SPDX-License-Identifier: MIT
// Original local RAM port semantics plus a read-only synchronous observation port.
module nes_native_ciram165(
 input wire clk,we,input wire [10:0] address,input wire [7:0] data,
 output reg [7:0] q,
 input wire [10:0] observe_address,output reg [7:0] observe_data
);
 (* ramstyle="M9K" *) reg [7:0] mem[0:2047];
 always @(posedge clk)begin
  if(we)mem[address]<=data;
  q<=mem[address];
  observe_data<=mem[observe_address];
 end
endmodule
