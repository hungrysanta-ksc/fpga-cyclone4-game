// SPDX-License-Identifier: MIT
// NES internal mono mix -> 512-clock box average -> DC rejection -> held CDC
// mailbox -> the serial timing used by the board-tested GBC DAC transmitter.
// No PSRAM writes, audio delay RAM, extra PLL, or game-clock backpressure.
module nes_dac162(
 input wire nes_clk,dac_clk,reset,input wire [15:0] inverted_sample,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT,
 output reg overrun
);
 (* async_reg="true" *) reg [1:0] nes_release,dac_release;
 always @(posedge nes_clk or posedge reset)
  if(reset)nes_release<=0;else nes_release<={nes_release[0],1'b1};
 always @(posedge dac_clk or posedge reset)
  if(reset)dac_release<=0;else dac_release<={dac_release[0],1'b1};
 wire nr=!nes_release[1],dr=!dac_release[1];
 // NES sample is FFFF minus the unsigned APU sum. Half scale bounds the
 // subsequent signed high-pass output without saturation or sign wrapping.
 wire [14:0] magnitude=~inverted_sample[15:1];
 reg [8:0] decimation;
 reg [23:0] sum;
 wire [23:0] sum_next=sum+{9'd0,magnitude};
 reg [14:0] average;
 reg filter_pending;
 reg signed [23:0] dc;
 wire signed [23:0] target={1'b0,average,8'd0};
 wire signed [23:0] delta=target-dc;
 wire signed [15:0] filtered=delta>>>8;
 reg signed [15:0] held_sample;
 reg request_toggle,ack_toggle;
 (* async_reg="true" *) reg [1:0] ack_sync,request_sync;
 always @(posedge nes_clk or posedge nr)begin
  if(nr)begin
   decimation<=0;sum<=0;average<=0;filter_pending<=0;dc<=0;
   held_sample<=0;request_toggle<=0;ack_sync<=0;overrun<=0;
  end else begin
   ack_sync<={ack_sync[0],ack_toggle};
   decimation<=decimation+1'b1;filter_pending<=0;
   if(decimation==511)begin
    average<=sum_next[23:9];sum<=0;filter_pending<=1;
   end else sum<=sum_next;
   if(filter_pending)begin
    dc<=dc+(delta>>>8);
    if(request_toggle==ack_sync[1])begin
     held_sample<=filtered;request_toggle<=!request_toggle;
    end else overrun<=1; // Never overwrite an unacknowledged sample.
   end
  end
 end
 reg signed [15:0] dac_sample;
 always @(posedge dac_clk or posedge dr)begin
  if(dr)begin request_sync<=0;ack_toggle<=0;dac_sample<=0;end
  else begin
   request_sync<={request_sync[0],request_toggle};
   if(request_sync[1]!=ack_toggle)begin
    dac_sample<=held_sample;ack_toggle<=request_sync[1];
   end
  end
 end
 // Same 84MHz /512 LRCK and /8 MCLK waveform as gbc_dac_psram.sv.
 // Mono is copied to both slots. Latch once per stereo frame to keep them equal.
 reg [8:0] divider;
 reg [2:0] mclk_pipe,lrck_pipe;
 reg [1:0] sclk_pipe;
 reg [15:0] stereo_sample,sample_shift;
 reg sdout_reg;
 wire mclk=divider[2],sclk=divider[3],lrck=divider[8];
 wire sclk_falling=({sclk_pipe[0],sclk}==2'b10);
 wire lrck_rising=({lrck_pipe[0],lrck}==2'b01);
 wire lrck_falling=({lrck_pipe[0],lrck}==2'b10);
 assign DAC_MCLK=~mclk_pipe[2];
 assign DAC_LRCK=lrck_pipe[2];
 assign DAC_SDOUT=sdout_reg;
 always @(posedge dac_clk or posedge dr)begin
  if(dr)begin
   divider<=9'h100;mclk_pipe<=0;lrck_pipe<=0;sclk_pipe<=0;
   stereo_sample<=0;sample_shift<=0;sdout_reg<=0;
  end else begin
   divider<=divider+1'b1;mclk_pipe<={mclk_pipe[1:0],mclk};
   lrck_pipe<={lrck_pipe[1:0],lrck};sclk_pipe<={sclk_pipe[0],sclk};
   if(sclk_falling)begin
    sdout_reg<=sample_shift[15];
    if(lrck_rising)begin stereo_sample<=dac_sample;sample_shift<=dac_sample;end
    else if(lrck_falling)sample_shift<=stereo_sample;
    else sample_shift<={sample_shift[14:0],1'b0};
   end
  end
 end
endmodule
