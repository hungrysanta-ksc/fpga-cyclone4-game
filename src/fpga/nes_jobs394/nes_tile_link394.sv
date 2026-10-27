// SPDX-License-Identifier: MIT
// One tile lifetime; job boundaries are exclusively owned by the host record
// executor. No chunk descriptor FIFO, autonomous append or seal FSM.
module nes_tile_link394(input wire nes_clk,host_clk,reset,source_fault,
 input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data,input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind,input wire [9:0] tile_slot,input wire [15:0] tile_generation,
 input wire end_valid,end_partial,output wire end_ready,input wire [15:0] end_generation,
 output wire word_valid,input wire word_ready,output wire word_end,word_partial,word_kind,output wire [15:0] word_generation,output wire [9:0] word_slot,output wire [5:0] word_length,
 input wire [4:0] read_at,output reg [7:0] read_data,output reg fault);
 wire rst=reset||source_fault;wire sr,hr;
 nes_domain_reset124 src_release(.clk(nes_clk),.raw_reset(rst),.reset(sr));
 nes_domain_reset124 dst_release(.clk(host_clk),.raw_reset(rst),.reset(hr));
 (* ramstyle="M9K, no_rw_check" *) reg [7:0] memory[0:31];
 reg pending,ending,kind;reg [15:0] generation;reg [9:0] slot;reg [5:0] length;reg [4:0] next_index;
 wire ready;
 nes_native_mailbox206 #(.WIDTH(34)) mailbox(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),.src_valid(pending&&!sr),.src_ready(ready),
  .src_data({ending,kind,generation,slot,length}),.dst_valid(word_valid),.dst_ready(word_ready&&!hr),.dst_data({word_end,word_kind,word_generation,word_slot,word_length}));
 assign word_partial=word_kind;
 assign tile_ready=!sr&&!fault&&!pending&&ready;
 assign end_ready=tile_ready&&next_index==0&&!tile_valid;
 wire valid_input=tile_kind<3&&tile_length==(tile_kind==1?32:16)&&(tile_kind!=1||tile_slot<128)&&(tile_kind!=2||tile_slot==0);
 always @(posedge nes_clk)if(tile_valid&&tile_ready&&valid_input&&tile_index==next_index)memory[tile_index]<=tile_data;
 always @(posedge host_clk)read_data<=memory[read_at];
 always @(posedge nes_clk or posedge sr)begin
  if(sr)begin fault<=0;pending<=0;ending<=0;kind<=0;generation<=0;slot<=0;length<=0;next_index<=0;end
  else begin
   if(pending&&ready)pending<=0;
   if(tile_valid&&tile_ready)begin
    if(!valid_input||tile_index!=next_index||(next_index!=0&&(kind!=(tile_kind==1)||generation!=tile_generation||slot!=tile_slot||length!=tile_length)))fault<=1;
    else begin
     if(next_index==0)begin kind<=tile_kind==1;generation<=tile_generation;slot<=tile_slot;length<=tile_length;ending<=0;end
     if(tile_index==tile_length-1)begin next_index<=0;pending<=1;end else next_index<=next_index+1'b1;
    end
   end else if(end_valid&&end_ready)begin ending<=1;kind<=end_partial;generation<=end_generation;pending<=1;end
  end
 end
endmodule
