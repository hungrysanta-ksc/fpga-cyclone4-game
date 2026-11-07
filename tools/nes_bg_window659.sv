// SPDX-License-Identifier: MIT
// A write in banks $52/$53 primes a tile. The matching read reports ready.
// DMA in $50/$51 consumes eight PSRAM words. Only two words can be ahead.
module nes_bg_window659(
 input wire clk,reset,stop,slot,safe,normal_request,mem_ready,mem_response,mem_error,
 input wire [21:0] mem_response_address,input wire [15:0] mem_word,
 input wire [23:0] address,input wire read_n,write_n,
 output wire issue,output wire [21:0] request_address,output reg owned,
 output wire selected,output wire [7:0] data,output reg fault
);
 wire prime_page=address[23:17]==7'h29, dma_page=address[23:17]==7'h28;
 reg active;reg [12:0] tag;reg [3:0] words;reg [4:0] consumed;
 reg [15:0] even_word,odd_word;
 reg read_held,write_held,read_ok;
 wire [3:0] used_words=consumed[4:1];
 wire [3:0] ready_words=words-used_words;
 // A byte in interleaved physical order maps back to its native NES
 // address. The normal reader applies the forward permutation at the pins.
 assign request_address={5'h10,tag,1'b0,words[2:0]};
 assign issue=active && !fault && !reset && !stop && !owned && words<8 && ready_words<2
              && slot && safe && !normal_request && mem_ready;
 wire match_tag=active && address[16:4]==tag;
 wire present=match_tag && consumed<16 && consumed[3:0]==address[3:0] && ready_words!=0;
 wire [15:0] word_now=consumed[1]?odd_word:even_word;
 assign selected=!reset && !stop && !read_n && (prime_page || dma_page || address==24'h540000);
 assign data=address==24'h540000 ?8'd1:prime_page?{fault,5'd0,consumed==16,match_tag && ready_words==2}:
             (present?(address[0]?word_now[7:0]:word_now[15:8]):8'd0);
 always @(posedge clk or posedge reset)begin
  if(reset)begin owned<=0;active<=0;fault<=0;words<=0;consumed<=0;tag<=0;
   read_held<=0;write_held<=0;read_ok<=0;end
  else begin
   // A STOP revokes the bus aperture immediately. The physical request
   // retains ownership until its outstanding response is discarded.
   if(issue)owned<=1;
   if(owned && mem_response)begin
    owned<=0;
    if(active && !stop)begin
     if(mem_error || mem_response_address!=request_address)fault<=1;
     else begin if(words[0])odd_word<=mem_word;else even_word<=mem_word;words<=words+1'b1;end
    end
   end
   if(stop)begin active<=0;read_held<=0;write_held<=0;read_ok<=0;end
   else begin
    if(!write_n && address==24'h546000)fault<=1;
    write_held<=prime_page && !write_n;
    if(prime_page && !write_n && !write_held)begin
     if(owned || (active && consumed!=16) || address[3:0]!=0)fault<=1;
     else begin active<=1;tag<=address[16:4];words<=0;consumed<=0;end
    end
    // Freeze availability on the first sampled read edge. A late PSRAM
    // response cannot retroactively validate a missed SNES byte.
    if(!read_held && dma_page && !read_n)begin read_held<=1;read_ok<=present;if(!present)fault<=1;end
    if(read_held && (read_n || !dma_page))begin
     read_held<=0;if(read_ok && !fault)consumed<=consumed+1'b1;
    end
   end
  end
 end
endmodule
