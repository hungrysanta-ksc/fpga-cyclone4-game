// SPDX-License-Identifier: MIT
// One 32-bit identity per admitted ROM lifetime, transferred before core release.
// BEGIN, data writes, STOP or fault cancel both handshake directions.
// Consumers see only a complete word, after the existing core-release barrier.
module nes_source_epoch207(
 input wire mem_clk,nes_clk,reset,local_reset,load_begin,load_valid,
 input wire loaded,run_enable,loader_fault,
 input wire [18:0] loaded_bytes,
 output wire source_ready,source_is_rom,source_writing,
 output wire [31:0] live_epoch
);
 reg [31:0] serial;
 reg exhausted;
 wire [31:0] next_serial=serial+32'd1;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin serial<=0;exhausted<=0;end
  else if(load_begin)begin
   if(serial==32'hffffffff)exhausted<=1;
   else serial<=next_serial;
  end
 end
 reg gray_pending;
 always @(posedge mem_clk or posedge reset)
  if(reset)gray_pending<=0;else gray_pending<=load_begin;

 // local_reset includes the long RAM scrub, so it masks publication only.
 wire invalid=reset||gray_pending||exhausted||loader_fault||!loaded||!run_enable||
              loaded_bytes!=19'h60000||load_begin||load_valid;
 wire tx_reset,rx_reset,held;
 nes_domain_reset124 tx_release(mem_clk,invalid,tx_reset);
 nes_domain_reset124 rx_release(nes_clk,invalid,rx_reset);
 nes_domain_reset124 release_ready(nes_clk,invalid||local_reset,held);

 reg [31:0] tx_shift,received;
 reg request,ack,active,complete;
 reg [4:0] bit_index;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] ack_mem,data_nes;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [2:0] request_nes;
 always @(posedge mem_clk or posedge tx_reset)
  if(tx_reset)ack_mem<=0;else ack_mem<={ack_mem[0],ack};
 always @(posedge nes_clk or posedge rx_reset)
  if(rx_reset)begin request_nes<=0;data_nes<=0;end
  else begin request_nes<={request_nes[1:0],request};data_nes<={data_nes[0],tx_shift[0]};end

 always @(posedge mem_clk or posedge tx_reset)begin
  if(tx_reset)begin tx_shift<=0;request<=0;active<=0;end
  else if(!active)begin
   tx_shift<=serial^(serial>>1);request<=1;active<=1;
  end else if(ack_mem[1]==request)begin
   tx_shift<={1'b0,tx_shift[31:1]};request<=!request;
  end
 end
 always @(posedge nes_clk or posedge rx_reset)begin
  if(rx_reset)begin received<=0;bit_index<=0;complete<=0;ack<=0;end
  else if(!complete&&request_nes[2]!=ack)begin
   received<={data_nes[1],received[31:1]};
   if(bit_index==31)complete<=1;
   else begin bit_index<=bit_index+1'b1;ack<=request_nes[2];end
  end
 end
 // Withhold the final bit's ACK so the source holds its final value until reset.
 reg delay_ready,admitted;
 reg [1:0] visible;
 always @(posedge nes_clk or posedge local_reset)
  if(local_reset)visible<=0;else visible<={visible[0],1'b1};
 always @(posedge nes_clk or posedge held)begin
  if(held)begin delay_ready<=0;admitted<=0;end
  else begin delay_ready<=1;admitted<=delay_ready&&complete&&!rx_reset;end
 end
 assign source_ready=!held&&admitted;
 assign source_is_rom=source_ready;
 assign source_writing=held||!admitted;
 assign live_epoch=visible[1]&&complete?received:32'd0;
endmodule
