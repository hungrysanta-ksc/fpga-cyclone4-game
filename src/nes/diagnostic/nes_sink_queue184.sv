// SPDX-License-Identifier: MIT
// Four immutable packets; one host-clock lifetime, COMMON reset only.
// E0 status20: dummy,F7,flags,acceptedBE16,retiredBE16,ACK12,CRC8.
// E1 stays command+16..256 packet bytes+CRC16BE. F6 clients must reject F7.
// Every SNES ACK is checked against the head packet BEFORE releasing credit.
module nes_sink_queue184(
 input wire clk,reset,enable,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,miso,
 input wire [7:0] sn_address,output wire [7:0] sn_data,
 output wire packet_ready,output wire [8:0] packet_length,
 input wire ack_write,input wire [3:0] ack_index,input wire [7:0] ack_byte,
 input wire ack_publish,output reg fault
);
 (* ramstyle="M9K" *) reg [7:0] buffer[0:1023];
 reg [8:0] lengths[0:3];
 reg [15:0] accepted,retired;
 wire [2:0] used=accepted[2:0]-retired[2:0];
 wire full=used==4;
 reg [95:0] ack_work,completed_ack;
 reg [11:0] ack_mask;
 reg ack_valid,checking,check_wait;
 reg [3:0] check_index;
 reg [7:0] read_data;
 wire [7:0] read_address=checking?{4'd0,check_index}:sn_address;
 always @(posedge clk)read_data<=buffer[{retired[1:0],read_address}];
 assign sn_data=read_data;
 assign packet_ready=used!=0&&!checking&&enable&&!reset&&!fault;
 assign packet_length=packet_ready?lengths[retired[1:0]]:9'd0;
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
 reg [151:0] snapshot;reg [7:0] reply,status_crc;
 reg crc_busy;reg [4:0] crc_position;integer j;
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire ours=command==8'he0||command==8'he1;
 wire [7:0] flags={fault,4'd0,full,ack_valid,(used!=0)};
 wire [16:0] expected_length={1'b0,payload_size}+17'd16;
 assign selected=!reset&&!SPI_SS&&ours&&byte_count!=0;
 assign miso=miso_hold;
 always @*begin
  reply=0;
  if(command==8'he0&&byte_count>=1&&byte_count<=19)reply=snapshot[8*(19-byte_count)+:8];
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   accepted<=0;retired<=0;ack_work<=0;completed_ack<=0;ack_mask<=0;ack_valid<=0;fault<=0;
   checking<=0;check_wait<=0;check_index<=0;
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;can_write<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;payload_size<=0;
   request_crc<=16'hffff;received_crc<=0;snapshot<=0;status_crc<=0;crc_busy<=0;crc_position<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(crc_busy)begin
    status_crc<=crc8(status_crc,snapshot[151-crc_position*8-:8]);
    if(crc_position==17)begin snapshot[7:0]<=crc8(status_crc,snapshot[151-crc_position*8-:8]);crc_busy<=0;end
    else crc_position<=crc_position+1'b1;
   end
   if(ack_write&&enable&&!fault)begin
    if(!packet_ready||ack_index>=12||ack_publish)fault<=1;
    else begin ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end
   end
   if(ack_publish&&enable&&!fault)begin
    if(!packet_ready||ack_mask!=12'hfff||ack_write||ack_work[95:80]!=16'h9a65)fault<=1;
    else begin checking<=1;check_wait<=0;check_index<=0;end
   end
   // Share the existing synchronous packet read port. SNES has finished the
   // packet; no new packet is visible until its complete ACK is validated.
   if(checking&&enable&&!fault)begin
    if(!check_wait)check_wait<=1;
    else begin
     check_wait<=0;
     if((check_index==0 && (ack_work[15:8]!=read_data || ack_work[7:0]!=(read_data==3?8'd1:8'd0))) ||
        (check_index!=0 && ack_work[check_index*8+:8]!=read_data))begin
      fault<=1;completed_ack<=ack_work;ack_valid<=1;
     end else if(check_index==9)begin
      retired<=retired+1'b1;completed_ack<=ack_work;ack_valid<=1;ack_mask<=0;checking<=0;
     end else check_index<=check_index==0?4'd2:check_index+1'b1;
    end
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bit_count];
   if(ss[1])begin
    bit_count<=0;byte_count<=0;command<=0;miso_hold<=0;request_crc<=16'hffff;payload_size<=0;received_crc<=0;
    if(!prev_ss&&ours)begin
     if(command==8'he0)begin if(byte_count!=20||bit_count!=0)fault<=1;end
     else if(!can_write||!enable||fault||payload_size>240||byte_count!=expected_length+3||bit_count!=0||received_crc!=request_crc)fault<=1;
     else begin lengths[accepted[1:0]]<=expected_length[8:0];accepted<=accepted+1'b1;end
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=511)byte_count<=byte_count+1'b1;
     if(byte_count==0)begin
      command<=incoming;can_write<=enable&&!full&&!fault;
      request_crc<=crc16(16'hffff,incoming);
      snapshot[151:144]<=8'hf7;snapshot[143:136]<=flags;
      snapshot[135:120]<=accepted;snapshot[119:104]<=retired;snapshot[7:0]<=0;
      status_crc<=0;crc_position<=0;crc_busy<=1;
      for(j=0;j<12;j=j+1)snapshot[103-j*8-:8]<=ack_valid?completed_ack[j*8+:8]:8'd0;
     end else if(command==8'he1)begin
      if(byte_count==13)payload_size[7:0]<=incoming;
      if(byte_count==14)payload_size[15:8]<=incoming;
      if(byte_count<=14||byte_count<=expected_length)begin
       request_crc<=crc16(request_crc,incoming);
       if(can_write&&byte_count<=256)buffer[{accepted[1:0],8'd0}+byte_count-1'b1]<=incoming;
      end else if(byte_count==expected_length+1)received_crc[15:8]<=incoming;
      else if(byte_count==expected_length+2)received_crc[7:0]<=incoming;
     end
    end
   end
  end
 end
endmodule
