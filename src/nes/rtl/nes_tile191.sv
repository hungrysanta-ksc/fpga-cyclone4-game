// SPDX-License-Identifier: MIT
// One metadata plan -> immutable SNES planar tile. Source must be sealed.
// Backend must flush old responses before mem_idle permits a new command.
module nes_tile191 #(parameter integer MAX_CYCLES=4096,parameter integer EXTERNAL_PLAN=0)(
 input wire clk,reset,stop,lease_valid,input wire [15:0] lease_generation,
 input wire plan_valid,output wire plan_ready,input wire [1:0] plan_kind,
 input wire [15:0] plan_generation,input wire [9:0] plan_slot,
 input wire [12:0] plan_tag,input wire [47:0] plan_rows,
 input wire [7:0] plan_mask,plan_alt_mask,input wire [103:0] plan_alt_tags,
 input wire mem_idle,mem_ready,output wire mem_request,mem_cancel,
 output wire [16:0] mem_address,output wire [15:0] mem_generation,
 input wire mem_response,mem_error,input wire [16:0] response_address,
 input wire [15:0] response_generation,input wire [7:0] response_data,
 output wire out_valid,input wire out_ready,output wire [7:0] out_data,
 output wire [4:0] out_index,output wire [5:0] out_length,
 output wire [1:0] out_kind,output wire [9:0] out_slot,output wire [15:0] out_generation,
 output wire busy,output reg fault,output reg done
);
 localparam IDLE=0,FETCH=1,WAIT=2,EMIT=3;
 reg [1:0] state,kind_q;reg [15:0] generation_q;reg [9:0] slot_q;
 reg [12:0] tag_q;reg [47:0] rows_q;reg [7:0] mask_q,alt_mask_q;reg [103:0] alt_tags_q;
 // External decoder owns these fields from handshake THROUGH done/cancel.
 // Constant parameter prunes the unused internal copy; default is unchanged.
 wire [1:0] kind=EXTERNAL_PLAN?plan_kind:kind_q;
 wire [15:0] generation=EXTERNAL_PLAN?plan_generation:generation_q;
 wire [9:0] slot=EXTERNAL_PLAN?plan_slot:slot_q;
 wire [12:0] tag=EXTERNAL_PLAN?plan_tag:tag_q;
 wire [47:0] rows=EXTERNAL_PLAN?plan_rows:rows_q;
 wire [7:0] mask=EXTERNAL_PLAN?plan_mask:mask_q,alt_mask=EXTERNAL_PLAN?plan_alt_mask:alt_mask_q;
 wire [103:0] alt_tags=EXTERNAL_PLAN?plan_alt_tags:alt_tags_q;
 reg [4:0] index;reg [31:0] cycles;
 reg [7:0] bytes[0:31]; // No reset; EMIT starts only after every byte is written.
 wire lease_ok=lease_valid&&lease_generation==generation;
 wire enabled=!reset&&!stop&&!fault;
 assign busy=state!=IDLE;
 assign plan_ready=enabled&&!busy&&lease_valid&&mem_idle&&!mem_response;
 assign mem_cancel=reset||stop||fault||(busy&&!lease_ok);
 wire zero_byte=kind==2||(kind==1&&(index>=16||!mask[index[3:1]]));
 wire [12:0] source_tag=(!index[0]&&alt_mask[index[3:1]])?
                       (alt_tags>>(index[3:1]*13)):tag;
 wire [2:0] source_row=rows>>(index[3:0]*3);
 assign mem_address={source_tag,index[0],source_row};
 assign mem_generation=generation;
 assign mem_request=enabled&&lease_ok&&state==FETCH&&!zero_byte&&!mem_response;
 assign out_valid=enabled&&lease_ok&&state==EMIT;
 assign out_data=bytes[index];assign out_index=index;
 assign out_length=kind==1?32:16;
 assign out_kind=kind;assign out_slot=slot;assign out_generation=generation;
 task advance;
  begin if(index==out_length-1)begin index<=0;state<=EMIT;end
        else begin index<=index+1'b1;state<=FETCH;end end
 endtask
 always @(posedge clk)begin
  if(reset||stop)begin
   state<=IDLE;kind_q<=0;generation_q<=0;slot_q<=0;tag_q<=0;rows_q<=0;mask_q<=0;
   alt_mask_q<=0;alt_tags_q<=0;index<=0;cycles<=0;fault<=0;done<=0;
  end else begin
   done<=0;
   if(busy)cycles<=cycles+1'b1;
   if(busy&&(!lease_ok||cycles>=MAX_CYCLES))begin fault<=1;state<=IDLE;end
   else if(!fault)case(state)
    IDLE:if(plan_valid&&plan_ready)begin
     if(plan_generation!=lease_generation||plan_kind==3||
        (plan_kind==0&&(plan_slot==0||plan_mask!=255))||
        (plan_kind==1&&(plan_slot>=128||plan_mask==0||plan_alt_mask!=0))||
        (plan_kind==2&&(plan_slot!=0||plan_tag!=0||plan_rows!=0||plan_mask!=0||plan_alt_mask!=0)))fault<=1;
     else begin
      kind_q<=plan_kind;generation_q<=plan_generation;slot_q<=plan_slot;tag_q<=plan_tag;
      rows_q<=plan_rows;mask_q<=plan_mask;alt_mask_q<=plan_alt_mask;alt_tags_q<=plan_alt_tags;
      index<=0;cycles<=0;state<=FETCH;
     end
    end
    FETCH:if(zero_byte)begin bytes[index]<=0;advance();end
          else if(mem_request&&mem_ready)state<=WAIT;
    WAIT:if(mem_response)begin
     if(mem_error||response_address!=mem_address||response_generation!=generation)begin fault<=1;state<=IDLE;end
     else begin bytes[index]<=response_data;advance();end
    end
    EMIT:if(out_valid&&out_ready)begin
     if(index==out_length-1)begin done<=1;state<=IDLE;index<=0;end
     else index<=index+1'b1;
    end
   endcase
  end
 end
endmodule
