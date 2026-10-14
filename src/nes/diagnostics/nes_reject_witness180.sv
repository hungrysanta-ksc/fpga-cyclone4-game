// SPDX-License-Identifier: MIT
// Passive NES-clock observation. No output feeds admission, release or transport.
// First observed error is sampled after the member's registered error update;
// it is NOT the exact CPU write or failed-fetch timestamp.
module nes_reject_witness180(
 input wire clk,reset,release_frame,collecting,owned,valid,
 input wire [15:0] generation,
 input wire [24:0] live_errors,final_errors,
 input wire [8:0] scanline,dot,input wire [7:0] mask,
 input wire [7:0] rows,objects,exceptions,
 input wire [5:0] groups,palettes,
 output wire sample_enable,output wire [95:0] sample
);
 reg armed,owned_seen,first_seen,previous_bad;
 // Payload is validity-qualified; no asynchronous payload reset tree.
 reg [25:0] first_position;
 reg [24:0] previous_signature;
 wire live_first=collecting && |live_errors;
 wire [25:0] position=first_seen?first_position:
                         live_first?{scanline,dot,mask}:{9'd511,9'd511,8'd0};
 wire new_owner=owned && !owned_seen && !release_frame && !reset;
 assign sample_enable=new_owner && armed &&
        (valid?previous_bad:(!previous_bad || final_errors!=previous_signature));
 // MSB first: kind2/gen8/errors25/line9/dot9/mask8/rows8/groups6/obj8/exc8/pal5.
 // kind1=reject, kind2=recovery. Ignore position on recovery. Missing first
 // error uses (511,511,0). Same error vector suppresses even a changed position.
 // Generation is modulo256; palette count saturates31 (valid maximum is2).
 assign sample={valid?2'd2:2'd1,generation[7:0],final_errors,
                position,
                rows,groups,objects,exceptions,palettes[5]?5'd31:palettes[4:0]};
 always @(posedge clk)begin
  if(reset)begin armed<=0;owned_seen<=0;first_seen<=0;previous_bad<=0;end
  else begin
   if(!owned)owned_seen<=0;
   if(release_frame)begin first_seen<=0;owned_seen<=0;end
   else begin
    if(armed && !first_seen && live_first)begin
     first_seen<=1;first_position<={scanline,dot,mask};
    end
    if(new_owner)begin
     owned_seen<=1;
     if(valid)begin armed<=1;previous_bad<=0;end
     else if(armed)begin previous_bad<=1;previous_signature<=final_errors;end
    end
   end
  end
 end
endmodule
