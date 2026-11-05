// SPDX-License-Identifier: MIT
// Observe the existing 33 map writes. Reads are gated by the caller's lease.
module nes_map_seal598(
 input wire clk, clear, copy, owned_valid, read_summary,
 input wire [4:0] write_group, read_group,
 input wire [5:0] column, groups,
 input wire [14:0] cell_word,
 output reg summary_hit,
 output wire [63:0] summary,
 output wire [15:0] map_crc
);
 function automatic [15:0] crc16_byte(input [15:0] crc,input [7:0] payload);
  reg [15:0] c;integer i;
  begin
   c=crc^{payload,8'b0};
   for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;
   crc16_byte=c;
  end
 endfunction
 function automatic [31:0] crc32_byte(input [31:0] crc,input [7:0] payload);
  reg [31:0] c;integer i;
  begin
   c=crc^payload;
   for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;
   crc32_byte=c;
  end
 endfunction
 reg [31:0] row_crc;
 reg [15:0] canonical_crc;
 reg [14:0] first_cell;
 wire [31:0] next_crc=crc32_byte(crc32_byte(column==0?32'hffffffff:row_crc,cell_word[7:0]),{1'b0,cell_word[14:8]});
 (* ramstyle="M9K" *) reg [63:0] descriptors[0:31];
 reg [63:0] q;
 always @(posedge clk)begin
  q<=descriptors[read_group];
  if(!clear && copy && column==32)
   descriptors[write_group]<={1'b0,cell_word,1'b0,first_cell,~next_crc};
 end
 always @(posedge clk)begin
  summary_hit<=!clear && read_summary && owned_valid && {1'b0,read_group}<groups;
  if(clear)canonical_crc<=16'hffff;
  else if(copy)begin
   canonical_crc<=crc16_byte(crc16_byte(canonical_crc,cell_word[7:0]),{1'b0,cell_word[14:8]});
   row_crc<=next_crc;
   if(column==0)first_cell<=cell_word;
  end
 end
 assign summary=owned_valid && !clear && summary_hit?q:64'd0;
 assign map_crc=owned_valid && !clear?canonical_crc:16'd0;
endmodule
