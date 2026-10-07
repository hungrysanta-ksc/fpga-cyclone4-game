// SPDX-License-Identifier: MIT
// 068 diagnostic-only wait after reset/PLL lock; not a voltage detector.
// At the specified board8 clock 1600 complete intervals give200us.
// VDD/VDDQ must already be stable before reset release for a tPU guarantee.
module nes_diag_startup_guard #(parameter integer WAIT_CYCLES=1600)(
 input wire clk,reset,output wire ready
);
 localparam WIDTH=$clog2(WAIT_CYCLES+1);
 reg [WIDTH-1:0] elapsed=0;
 reg armed=0,done=0;
 assign ready=!reset&&done;
 always @(posedge clk or posedge reset)begin
  if(reset)begin elapsed<=0;armed<=0;done<=0;end
  else if(!armed)armed<=1;
  else if(!done)begin
   if(elapsed==WIDTH'(WAIT_CYCLES-1))done<=1;
   else elapsed<=elapsed+1'b1;
  end
 end
endmodule
