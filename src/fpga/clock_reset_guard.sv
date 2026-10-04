// Asynchronous assertion even when the generated clock stops, synchronous
// two-edge release after all PLLs report lock. Does not model analog locking.
module clock_reset_guard(input wire clk,external_reset,locked,output wire reset);
 wire fault=external_reset||!locked;
 reg[1:0]release_pipe;
 always @(posedge clk or posedge fault)
  if(fault)release_pipe<=0;else release_pipe<={release_pipe[0],1'b1};
 assign reset=fault||!release_pipe[1];
endmodule
