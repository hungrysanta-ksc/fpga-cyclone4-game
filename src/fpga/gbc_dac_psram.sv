// GBC APU -> CIC/64 -> PSRAM stereo delay -> FXPAK Pro serial DAC pins.
module gbc_dac_psram #(
 parameter [12:0] DELAY_SAMPLES=13'd5075
)(
 input wire mute,
 input wire clk_audio,input wire reset_audio,input wire audio_ce,
 input wire signed[15:0]audio_l,audio_r,input wire clk_dac,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT,
 output wire req_valid,req_write,output wire[22:0]req_addr,output wire[15:0]req_wdata,
 input wire req_ready,input wire rsp_valid,input wire[15:0]rsp_rdata,
 output wire delay_protocol_error,output wire delay_sample_overrun
);
 localparam integer CIC_BITS=16+3*6;
 reg signed[CIC_BITS-1:0]int0_l,int1_l,int2_l,int0_r,int1_r,int2_r;
 reg signed[CIC_BITS-1:0]delay0_l,delay1_l,delay2_l,delay0_r,delay1_r,delay2_r;
 reg[5:0]decimation_count;
 reg signed[15:0]filtered_l,filtered_r;
 reg filtered_valid;
 wire signed[CIC_BITS-1:0]input_l_ext={{(CIC_BITS-16){audio_l[15]}},audio_l};
 wire signed[CIC_BITS-1:0]input_r_ext={{(CIC_BITS-16){audio_r[15]}},audio_r};
 wire signed[CIC_BITS-1:0]int0_l_next=int0_l+input_l_ext;
 wire signed[CIC_BITS-1:0]int1_l_next=int1_l+int0_l_next;
 wire signed[CIC_BITS-1:0]int2_l_next=int2_l+int1_l_next;
 wire signed[CIC_BITS-1:0]int0_r_next=int0_r+input_r_ext;
 wire signed[CIC_BITS-1:0]int1_r_next=int1_r+int0_r_next;
 wire signed[CIC_BITS-1:0]int2_r_next=int2_r+int1_r_next;
 wire signed[CIC_BITS-1:0]comb0_l_next=int2_l_next-delay0_l;
 wire signed[CIC_BITS-1:0]comb1_l_next=comb0_l_next-delay1_l;
 wire signed[CIC_BITS-1:0]comb2_l_next=comb1_l_next-delay2_l;
 wire signed[CIC_BITS-1:0]comb0_r_next=int2_r_next-delay0_r;
 wire signed[CIC_BITS-1:0]comb1_r_next=comb0_r_next-delay1_r;
 wire signed[CIC_BITS-1:0]comb2_r_next=comb1_r_next-delay2_r;
 always @(posedge clk_audio)begin
  filtered_valid<=0;
  if(reset_audio)begin
   int0_l<=0;int1_l<=0;int2_l<=0;int0_r<=0;int1_r<=0;int2_r<=0;
   delay0_l<=0;delay1_l<=0;delay2_l<=0;delay0_r<=0;delay1_r<=0;delay2_r<=0;
   decimation_count<=0;filtered_l<=0;filtered_r<=0;filtered_valid<=0;
  end else if(audio_ce)begin
   int0_l<=int0_l_next;int1_l<=int1_l_next;int2_l<=int2_l_next;
   int0_r<=int0_r_next;int1_r<=int1_r_next;int2_r<=int2_r_next;
   decimation_count<=decimation_count+1'b1;
   if(decimation_count==0)begin
    delay0_l<=int2_l_next;delay1_l<=comb0_l_next;delay2_l<=comb1_l_next;
    delay0_r<=int2_r_next;delay1_r<=comb0_r_next;delay2_r<=comb1_r_next;
    filtered_l<=comb2_l_next[CIC_BITS-1:18];filtered_r<=comb2_r_next[CIC_BITS-1:18];
    filtered_valid<=1;
   end
  end
 end

 wire delay_ready,delay_busy,delayed_valid;
 wire signed[15:0]delayed_l,delayed_r;
 audio_psram_delay_client delay_client(clk_audio,reset_audio,
  filtered_valid,filtered_l,filtered_r,DELAY_SAMPLES,delay_ready,delay_busy,
  delayed_valid,delayed_l,delayed_r,req_valid,req_write,req_addr,req_wdata,
  req_ready,rsp_valid,rsp_rdata,delay_protocol_error,delay_sample_overrun);

 reg signed[15:0]playback_l,playback_r;
 reg sample_toggle;
 always @(posedge clk_audio)begin
  if(reset_audio)begin playback_l<=0;playback_r<=0;sample_toggle<=0;end
  else if(delayed_valid)begin playback_l<=delayed_l;playback_r<=delayed_r;sample_toggle<=~sample_toggle;end
 end

 (* async_reg = "true" *) reg[1:0]toggle_sync;
 reg toggle_seen;reg signed[15:0]dac_sample_l,dac_sample_r;
 (* async_reg="true" *)reg[1:0]dac_reset_pipe;
 always @(posedge clk_dac or posedge reset_audio)begin
  if(reset_audio)dac_reset_pipe<=2'b11;else dac_reset_pipe<={dac_reset_pipe[0],1'b0};
 end
 always @(posedge clk_dac)begin
  if(dac_reset_pipe[1])begin toggle_sync<=0;toggle_seen<=0;dac_sample_l<=0;dac_sample_r<=0;end
  else begin
   toggle_sync<={toggle_sync[0],sample_toggle};
   if(toggle_sync[1]!=toggle_seen)begin
    toggle_seen<=toggle_sync[1];dac_sample_l<=playback_l;dac_sample_r<=playback_r;
   end
  end
 end

 (* async_reg="true" *)reg[1:0]mute_sync;
 always @(posedge clk_dac)begin
  if(dac_reset_pipe[1])mute_sync<=0;else mute_sync<={mute_sync[0],mute};
 end
 reg[8:0]divider;reg[2:0]mclk_pipe,lrck_pipe;reg[1:0]sclk_pipe;
 reg[15:0]sample_shift;reg sdout_reg;
 wire mclk=divider[2],sclk=divider[3],lrck=divider[8];
 wire sclk_falling=({sclk_pipe[0],sclk}==2'b10);
 wire lrck_rising=({lrck_pipe[0],lrck}==2'b01);
 wire lrck_falling=({lrck_pipe[0],lrck}==2'b10);
 wire signed[15:0]selected_sample=mute_sync[1]?16'b0:(lrck?dac_sample_l:dac_sample_r);
 assign DAC_MCLK=~mclk_pipe[2];assign DAC_LRCK=lrck_pipe[2];assign DAC_SDOUT=sdout_reg;
 always @(posedge clk_dac)begin
  if(dac_reset_pipe[1])begin
   divider<=9'h100;mclk_pipe<=0;lrck_pipe<=0;sclk_pipe<=0;sample_shift<=0;sdout_reg<=0;
  end else begin
   divider<=divider+1'b1;mclk_pipe<={mclk_pipe[1:0],mclk};lrck_pipe<={lrck_pipe[1:0],lrck};sclk_pipe<={sclk_pipe[0],sclk};
   if(sclk_falling)begin
    sdout_reg<=sample_shift[15];
    if(lrck_rising||lrck_falling)sample_shift<=selected_sample;
    else sample_shift<={sample_shift[14:0],1'b0};
   end
  end
 end
endmodule
