// SPDX-License-Identifier: MIT
// Observation only. Counts reference /16 rising edges in exactly WINDOW board
// clock cycles. Convert to Hz ONLY when board clock frequency is established.
// No memory controller, PLL, RUN command, or path to external memory exists.
module nes_clock_observation087 #(parameter integer WINDOW=8000000)(
 input wire clk,ref_clk,ss,sck,mosi,
 output wire miso,drive,ready
);
 reg [3:0] divider=0;
 always @(posedge ref_clk)divider<=divider+1'b1;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] ref_sync=0,ss_sync=3,sck_sync=0,mosi_sync=0;
 reg ref_previous=0,ss_previous=1,sck_previous=0;
 always @(posedge clk)begin
  ref_sync<={ref_sync[0],divider[3]};
  ss_sync<={ss_sync[0],ss};sck_sync<={sck_sync[0],sck};mosi_sync<={mosi_sync[0],mosi};
  ref_previous<=ref_sync[1];ss_previous<=ss_sync[1];sck_previous<=sck_sync[1];
 end
 wire edge_seen=ref_sync[1]&&!ref_previous;
 reg [6:0] age=127;
 reg [31:0] cycles=0,count=0,published_count=0,window_sequence=0;
 reg valid=0,ever_gap=0,window_gap=0,published_gap=0;
 wire live=age<64;
 always @(posedge clk)begin
  if(edge_seen)age<=0;else if(age!=127)age<=age+1'b1;
  if(!live)ever_gap<=1;
  if(cycles==WINDOW-1)begin
   cycles<=0;count<=0;published_count<=count+edge_seen;
   if(window_sequence!=32'hffffffff)window_sequence<=window_sequence+1'b1;
   valid<=1;published_gap<=window_gap||!live;window_gap<=0;
  end else begin
   cycles<=cycles+1'b1;if(edge_seen)count<=count+1'b1;
   if(!live)window_gap<=1;
  end
 end
 // C0 latches all16 bytes atomically after the command byte. Commands CF/C0
 // respond beginning at the next byte. Unknown commands and overread return0.
 // Snapshot byte0=87,byte1={0,window_gap,ever_gap,live,valid},2..5window_sequence,
 // 6..9count,10..13WINDOW,14=16(divisor),15=0, multi-byte integers LE.
 reg [127:0] snapshot=0;
 reg [7:0] shift=0,command=0;
 reg [2:0] bit_count=0;
 reg [5:0] byte_count=0;
 reg miso_hold=0;
 wire [7:0] reply=command==8'hcf ? 8'h87 :
   command==8'hc0 && byte_count>=1 && byte_count<=16 ? snapshot[(byte_count-1)*8+:8]:8'h00;
 assign miso=miso_hold;
 assign drive=!ss;
 assign ready=1'b1; // SPI service only: NOT frequency, liveness or memory READY.
 always @(posedge clk)begin
  if(ss_sync[1])begin
   bit_count<=0;byte_count<=0;command<=0;shift<=0;miso_hold<=0;
  end else begin
   if(!sck_sync[1]&&sck_previous)miso_hold<=reply[7-bit_count];
   if(sck_sync[1]&&!sck_previous)begin
    shift<={shift[6:0],mosi_sync[1]};bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=63)byte_count<=byte_count+1'b1;
     if(byte_count==0)begin
      command<={shift[6:0],mosi_sync[1]};
      if({shift[6:0],mosi_sync[1]}==8'hc0)
       snapshot<={8'd0,8'd16,32'(WINDOW),published_count,window_sequence,
                  4'b0,published_gap,ever_gap,live,valid,8'h87};
     end
    end
   end
  end
 end
endmodule
