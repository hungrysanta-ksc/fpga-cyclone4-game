// SPDX-License-Identifier: MIT
// Read-only mode-0 SPI observer, command70. Runs on the NES source clock.
// <=250kHz SCK, >=1us CS setup/hold. Seven response bytes after command:
// D4, flags(bit0 core held, bit1 sticky ROM fault), first error, samples32 BE.
// Counts valid CPU ROM sample events (including cache hits), NOT instructions.
// All snapshot fields originate in this domain. No live multibit CDC sampling.
module nes_run_observer134(
 input wire clk,reset,core_reset,cpu_sample,rom_fault,
 input wire [3:0] rom_error,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,output wire miso
);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] ss_sync,sck_sync,mosi_sync;
 reg sck_previous;
 reg [2:0] bit_count;
 reg [3:0] byte_count;
 reg [7:0] shift,command;
 reg [31:0] samples;
 reg sticky_fault;
 reg [3:0] first_error;
 reg [55:0] snapshot;
 reg miso_hold;
 wire [7:0] incoming={shift[6:0],mosi_sync[1]};
 reg [7:0] reply;
 assign selected=!reset && !SPI_SS && command==8'h70 && byte_count!=0;
 assign miso=miso_hold;
 always @* begin
  case(byte_count)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];
   4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];
   7:reply=snapshot[7:0];default:reply=0;
  endcase
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   ss_sync<=3;sck_sync<=0;mosi_sync<=0;sck_previous<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;miso_hold<=0;snapshot<=0;
   samples<=0;sticky_fault<=0;first_error<=0;
  end else begin
   ss_sync<={ss_sync[0],SPI_SS};sck_sync<={sck_sync[0],SPI_SCK};mosi_sync<={mosi_sync[0],SPI_MOSI};
   sck_previous<=sck_sync[1];
   if(cpu_sample && !core_reset && samples!=32'hffffffff)samples<=samples+1'b1;
   if(rom_fault && !sticky_fault)begin sticky_fault<=1;first_error<=rom_error;end
   if(ss_sync[1])begin bit_count<=0;byte_count<=0;command<=0;miso_hold<=0;end
   else begin
    if(!sck_sync[1] && sck_previous)miso_hold<=reply[7-bit_count];
    if(sck_sync[1] && !sck_previous)begin
     shift<=incoming;bit_count<=bit_count+1'b1;
     if(bit_count==7)begin
      if(byte_count!=9)byte_count<=byte_count+1'b1;
      if(byte_count==0)begin
       command<=incoming;
       snapshot<={8'hd4,6'd0,sticky_fault,core_reset,4'd0,first_error,samples};
      end
     end
    end
   end
  end
 end
endmodule
