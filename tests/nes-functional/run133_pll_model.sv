// SPDX-License-Identifier: MIT
// Test-only clocks. No analog PLL lock/frequency or physical timing claim.
`timescale 1ns/1ps
module nes_clock_pll123(input wire areset,inclk0,output reg c0=0,c1=0,output wire locked);
 reg memory_running=1;
 always #5.952 c0=~c0;
 always #2.976 if(memory_running)c1=~c1;
 assign locked=!areset;
endmodule
