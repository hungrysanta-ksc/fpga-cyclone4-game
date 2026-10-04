// Capture error becomes visible one edge after the offending input. Preserve
// that edge's pipeline stage without feeding state back into a pipeline child.
module gbc_fault_stage(
 input wire clk,reset,first_fault,input wire[4:0]stage,
 output reg[4:0]frozen_stage
);
 reg[4:0]previous_stage;
 always @(posedge clk)begin
  if(reset)begin previous_stage<=0;frozen_stage<=0;end
  else begin
   previous_stage<=stage;
   if(first_fault)frozen_stage<=previous_stage;
  end
 end
endmodule
