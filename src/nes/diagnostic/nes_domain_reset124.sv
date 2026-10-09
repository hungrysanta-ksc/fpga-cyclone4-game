// SPDX-License-Identifier: MIT
// Diagnostic integration: common asynchronous assertion, local two-edge release.
// A stopped clock keeps reset asserted. All participating domains share raw_reset.
// This does not detect stopped clocks or guarantee a physical abort deadline.
module nes_domain_reset124(input wire clk,raw_reset,output wire reset);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] release_reset;
 always @(posedge clk or posedge raw_reset)
  if(raw_reset)release_reset<=2'b11;
  else release_reset<={release_reset[0],1'b0};
 assign reset=release_reset[1];
endmodule
