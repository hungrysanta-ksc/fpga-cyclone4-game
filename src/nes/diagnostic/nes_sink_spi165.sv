// SPDX-License-Identifier: MIT
// Reverse transport: MCU -> one immutable SNES packet -> coherent ACK.
// E0 status16: dummy,F6,flags,ACK[12],CRC8. E1: command,packet[16..256],CRC16BE.
// CRC16 CCITT initFFFF covers command+packet; CRC8 poly07 init0 covers status1..14.
module nes_sink_spi165(
 input wire clk,reset,enable,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,output wire miso,
 input wire [7:0] sn_address,output reg [7:0] sn_data,
 output wire packet_ready,output wire [8:0] packet_length,
 input wire ack_write,input wire [3:0] ack_index,input wire [7:0] ack_byte,
 input wire ack_publish,output reg fault
);
 (* ramstyle="M9K" *) reg [7:0] buffer[0:255];
 reg sealed,ack_valid;reg [8:0] length;
 reg [95:0] ack_work,ack_held;reg [11:0] ack_mask;
 always @(posedge clk)sn_data<=buffer[sn_address];
 assign packet_ready=sealed&&enable&&!reset&&!fault;
 assign packet_length=packet_ready?length:9'd0;
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};for(j=0;j<8;j=j+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 function automatic [7:0] crc8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end
 endfunction
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck,miso_hold,can_write;
 reg [2:0] bit_count;reg [8:0] byte_count;
 reg [7:0] shift,command;reg [15:0] payload_size,request_crc,received_crc;
 reg [119:0] snapshot;reg [7:0] reply,status_crc;integer j;
 reg crc_busy;reg [3:0] crc_position;
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire ours=command==8'he0||command==8'he1;
 wire [7:0] flags={fault,5'd0,ack_valid,sealed};
 wire [16:0] expected_length={1'b0,payload_size}+17'd16;
 assign selected=!reset&&!SPI_SS&&ours&&byte_count!=0;
 assign miso=miso_hold;
 always @*begin
  reply=0;
  if(command==8'he0&&byte_count>=1&&byte_count<=15)reply=snapshot[8*(15-byte_count)+:8];
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   sealed<=0;length<=0;ack_valid<=0;ack_work<=0;ack_held<=0;ack_mask<=0;fault<=0;
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;can_write<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;payload_size<=0;
   request_crc<=16'hffff;received_crc<=0;snapshot<=0;status_crc<=0;crc_busy<=0;crc_position<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   // Fourteen byte steps, not one long combinational CRC chain. At84MHz this
   // finishes long before the CRC reply byte at2.625MHz SPI.
   if(crc_busy)begin
    status_crc<=crc8(status_crc,snapshot[119-crc_position*8-:8]);
    if(crc_position==13)begin snapshot[7:0]<=crc8(status_crc,snapshot[119-crc_position*8-:8]);crc_busy<=0;end
    else crc_position<=crc_position+1'b1;
   end
   if(ack_write&&enable&&!fault)begin
    if(!sealed||ack_index>=12)fault<=1;
    else begin ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end
   end
   if(ack_publish&&enable&&!fault)begin
    if(!sealed||ack_mask!=12'hfff)fault<=1;
    else begin ack_held<=ack_work;ack_valid<=1;sealed<=0;ack_mask<=0;end
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bit_count];
   if(ss[1])begin
    bit_count<=0;byte_count<=0;command<=0;miso_hold<=0;request_crc<=16'hffff;payload_size<=0;received_crc<=0;
    if(!prev_ss&&ours)begin
     if(command==8'he0)begin if(byte_count!=16||bit_count!=0)fault<=1;end
     else if(!can_write||!enable||fault||payload_size>240||byte_count!=expected_length+3||bit_count!=0||received_crc!=request_crc)fault<=1;
     else begin sealed<=1;length<=expected_length[8:0];ack_valid<=0;ack_mask<=0;end
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=511)byte_count<=byte_count+1'b1;
     if(byte_count==0)begin
      command<=incoming;can_write<=enable&&!sealed&&!fault;
      request_crc<=crc16(16'hffff,incoming);
      snapshot[119:112]<=8'hf6;snapshot[111:104]<=flags;snapshot[7:0]<=0;
      status_crc<=0;crc_position<=0;crc_busy<=1;
      for(j=0;j<12;j=j+1)snapshot[103-j*8-:8]<=ack_held[j*8+:8];
     end else if(command==8'he1)begin
      if(byte_count==13)payload_size[7:0]<=incoming;
      if(byte_count==14)payload_size[15:8]<=incoming;
      if(byte_count<=14||byte_count<=expected_length)begin
       request_crc<=crc16(request_crc,incoming);
       if(can_write&&byte_count<=256)buffer[byte_count-1'b1]<=incoming;
      end else if(byte_count==expected_length+1)received_crc[15:8]<=incoming;
      else if(byte_count==expected_length+2)received_crc[7:0]<=incoming;
     end
    end
   end
  end
 end
endmodule
