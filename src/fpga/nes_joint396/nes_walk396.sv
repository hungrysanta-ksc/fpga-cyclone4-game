// SPDX-License-Identifier: MIT
// NES clock's single field execution cursor:source footer6 writes or
// decoded-plan byte fetch/capture. Neither client owns a second phase FSM.
module nes_walk396(input wire clk,reset,source_request,plan_request,
 output wire source_capture,plan_capture,output wire [2:0] source_index);
 localparam NONE=0,SOURCE=1,PLAN=2;
 reg [1:0] owner;reg phase;reg [2:0] index;
 assign source_index=index;
 assign source_capture=!reset&&owner==SOURCE&&phase;
 assign plan_capture=!reset&&owner==PLAN&&phase&&plan_request;
 always @(posedge clk or posedge reset)begin
  if(reset)begin owner<=NONE;phase<=0;index<=0;end
  else case(owner)
   NONE:begin phase<=0;index<=0;if(source_request)owner<=SOURCE;else if(plan_request)owner<=PLAN;end
   SOURCE:if(!source_request)begin owner<=NONE;phase<=0;end
    else if(!phase)phase<=1;
    else begin phase<=0;if(index==5)begin owner<=NONE;index<=0;end else index<=index+1'b1;end
   PLAN:if(!plan_request)begin owner<=NONE;phase<=0;end
    else if(!phase)phase<=1;
    else begin phase<=0;if(source_request)begin owner<=SOURCE;index<=0;end end
   default:owner<=NONE;
  endcase
 end
endmodule
