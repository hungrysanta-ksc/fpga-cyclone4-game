// SPDX-License-Identifier: MIT
// Mode0 E8 status20, E9 length/payload/CRC16BE/CRC8/A5 (length+6).
// Same host clock as196 RAM and193 descriptor. No SPI consume command:
// only SNES194 consumes a chunk. reset/STOP must cancel ALL endpoints.
module nes_plan_spi197(
 input wire clk,reset,enable,stop,source_fault,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,miso,output reg fault,
 input wire plan_idle,plan_ready,output reg plan_write,output reg [7:0] plan_data,
 output reg plan_seal,output reg [5:0] plan_length,output reg [15:0] plan_crc,
 input wire chunk_ready,chunk_kind,input wire [11:0] chunk_length,
 input wire [9:0] chunk_slot,input wire [15:0] chunk_generation,
 input wire [31:0] chunk_token,input wire end_sealed
);
 wire raw=reset||stop||!enable;wire local_reset;
 nes_domain_reset124 release_local(.clk(clk),.raw_reset(raw),.reset(local_reset));
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck,miso_hold,can_write,ended;
 reg [2:0] bits;reg [5:0] count;reg [7:0] shift,command,length,tail,received8,request8;
 reg [15:0] received16,accepted;
 reg [151:0] snapshot;reg [7:0] status_crc,reply;reg crc_busy;reg [4:0] crc_at;
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire ours=command==8'he8||command==8'he9;
 wire live=enable&&!raw&&!local_reset&&!fault&&!source_fault;
 assign selected=!raw&&!SPI_SS&&ours&&count!=0;
 assign miso=miso_hold;
 wire [15:0] offset=chunk_kind?{1'b0,chunk_slot,5'b0}:{2'b0,chunk_slot,4'b0};
 function automatic [7:0] crc8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end
 endfunction
 always @*begin
  reply=0;if(command==8'he8&&count>=1&&count<=19)reply=snapshot[(19-count)*8+:8];
 end
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;
   bits<=0;count<=0;shift<=0;command<=0;length<=0;tail<=0;received8<=0;request8<=0;received16<=0;
   fault<=0;can_write<=0;ended<=0;accepted<=0;plan_write<=0;plan_seal<=0;plan_data<=0;plan_length<=0;plan_crc<=0;
   snapshot<=0;status_crc<=0;crc_busy<=0;crc_at<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   plan_write<=0;plan_seal<=0;
   if(source_fault)fault<=1; // Sticky independently of downstream cancellation.
   if(end_sealed)ended<=1;
   if(crc_busy)begin
    status_crc<=crc8(status_crc,snapshot[151-crc_at*8-:8]);
    if(crc_at==17)begin snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_at*8-:8]);crc_busy<=0;end
    else crc_at<=crc_at+1'b1;
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bits];
   if(ss[1])begin
    bits<=0;count<=0;command<=0;miso_hold<=0;request8<=0;length<=0;received16<=0;received8<=0;tail<=0;
    if(!prev_ss&&ours)begin
     if(command==8'he8)begin if(count!=20||bits!=0)fault<=1;end
     else if(!can_write||!live||length<16||length>32||length[0]||count!=length+6||bits!=0||received8!=request8||tail!=8'ha5)fault<=1;
     else begin plan_length<=length[5:0];plan_crc<=received16;plan_seal<=1;accepted<=accepted+1'b1;end
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bits<=bits+1'b1;
    if(bits==7)begin
     if(count!=63)count<=count+1'b1;
     if(count==0)begin
      command<=incoming;can_write<=live&&plan_idle&&accepted!=16'hffff;
      request8<=crc8(0,incoming);
      // Descriptor is held by193 until SNES consume. Snapshot at command end.
      snapshot<={8'hd7,8'd1,{fault||source_fault,5'd0,ended,live&&plan_idle&&accepted!=16'hffff},accepted,
       chunk_ready?8'd1:8'd0,chunk_ready?{7'd0,chunk_kind}:8'd0,
       chunk_ready?chunk_length[7:0]:8'd0,chunk_ready?{4'd0,chunk_length[11:8]}:8'd0,
       chunk_ready?offset[7:0]:8'd0,chunk_ready?offset[15:8]:8'd0,
       chunk_ready?chunk_generation[7:0]:8'd0,chunk_ready?chunk_generation[15:8]:8'd0,
       chunk_ready?chunk_token[7:0]:8'd0,chunk_ready?chunk_token[15:8]:8'd0,
       chunk_ready?chunk_token[23:16]:8'd0,chunk_ready?chunk_token[31:24]:8'd0,8'd0,8'd0};
      status_crc<=0;crc_busy<=1;crc_at<=0;
     end else if(command==8'he9)begin
      if(count<=length+3||count==1)request8<=crc8(request8,incoming);
      if(count==1)begin length<=incoming;if(incoming<16||incoming>32||incoming[0])fault<=1;end
      else if(count<=length+1)begin
       if(can_write&&live&&plan_ready)begin plan_write<=1;plan_data<=incoming;end
       else fault<=1;
      end else if(count==length+2)received16[15:8]<=incoming;
      else if(count==length+3)received16[7:0]<=incoming;
      else if(count==length+4)received8<=incoming;
      else if(count==length+5)tail<=incoming;
     end
    end
   end
  end
 end
endmodule
