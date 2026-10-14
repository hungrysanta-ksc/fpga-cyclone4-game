// SPDX-License-Identifier: MIT
// Schema3: first rejected owned geometry after valid, then first recovery.
// No first-error position and no changes within a continuous rejection episode.
module nes_reject_witness180(
 input wire clk,reset,release_frame,collecting,owned,valid,
 input wire [15:0] generation,
 input wire [24:0] live_errors,final_errors,
 input wire [8:0] scanline,dot,input wire [7:0] mask,
 input wire [7:0] rows,objects,exceptions,
 input wire [5:0] groups,palettes,
 output wire sample_enable,output wire [95:0] sample
);
 reg armed,owned_seen,previous_bad;
 wire new_owner=owned && !owned_seen && !release_frame && !reset;
 assign sample_enable=new_owner && armed && (valid?previous_bad:!previous_bad);
 // Retain final errors/counts without duplicate payload FF. The mask is the
 // candidate's display_mask, NOT PPUMASK at the first observed error.
 assign sample={valid?2'd2:2'd1,generation[7:0],final_errors,9'd511,9'd511,mask,
   rows,groups,objects,exceptions,palettes[5]?5'd31:palettes[4:0]};
 always @(posedge clk)begin
  if(reset)begin armed<=0;owned_seen<=0;previous_bad<=0;end
  else begin
   if(!owned || release_frame)owned_seen<=0;
   else if(new_owner)begin
    owned_seen<=1;
    if(valid)begin armed<=1;previous_bad<=0;end
    else if(armed)previous_bad<=1;
   end
  end
 end
endmodule
