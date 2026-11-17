// SPDX-License-Identifier: MIT
// Four immutable packets; one host-clock lifetime, COMMON reset only.
// E0 status20: dummy,F7,flags,acceptedBE16,retiredBE16,ACK12,CRC8.
// E1 stays command+16..256 packet bytes+CRC16BE. F6 clients must reject F7.
// Every SNES ACK is checked against the head packet BEFORE releasing credit.
module nes_sink_spi165(
 input wire clk,reset,enable,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire selected,miso,
 input wire completed_read,completed_valid,input wire [7:0] completed_address,
 input wire [7:0] sn_address,output wire [7:0] sn_data,
 output wire packet_ready,output wire [8:0] packet_length,
 input wire ack_write,input wire [3:0] ack_index,input wire [7:0] ack_byte,
 input wire ack_publish,map_progress,stop,output reg fault
);
 (* ramstyle="M9K" *) reg [7:0] buffer[0:1023];
 reg [8:0] lengths[0:3];
 reg [15:0] accepted,retired;
 wire [2:0] used=accepted[2:0]-retired[2:0];
 wire full=used==4;
 reg [95:0] ack_work;
 reg [11:0] ack_mask;
 reg ack_valid,checking,compare_pending;
 reg progress;
 reg [3:0] compare_index;
 reg [7:0] compare_byte;
 reg [7:0] read_data;
 // Compare the written ACK byte against the immutable head one clock later.
 // On the cartridge bus an ACK write and an aperture read exclude each other.
 wire [7:0] read_address=ack_write?{4'b0,ack_index[3:1],ack_index[0]&&(|ack_index[3:1])}:sn_address;
 // Encoded lengths above 256 distinguish compressed slots.
 reg opcode_nine, receiving_rows, canceled_rows;
 wire [8:0] head_length=lengths[retired[1:0]];
 wire compact=head_length[8] && |head_length[7:6];
 wire [7:0] observed_opcode=compact?8'd2:read_data;
 wire compare_ok=compare_index==0 ? compare_byte==(observed_opcode==3?1:0) :
                 compare_index==1 ? compare_byte==observed_opcode :
                 compare_index==10 ? compare_byte==8'h65 :
                 compare_index==11 ? compare_byte==8'h9a : compare_byte==read_data;
 always @(posedge clk)read_data<=buffer[{retired[1:0],read_address}];
 reg [7:0] expected_read;
 reg return_zero, return_data_opcode;
 // Header is 16 bytes. At each 64-byte wrap, only columns 16..33 are literal.
 wire literal_column=(sn_address[5:4]==2'b01)||(sn_address[5:1]==5'd16);
 always @(posedge clk) begin
  return_zero<=compact && sn_address>=16 && !literal_column;
  return_data_opcode<=compact && sn_address==0;
 end
 assign sn_data=return_zero?8'd0:return_data_opcode?8'd2:read_data;
 assign packet_ready=used!=0&&!checking&&enable&&!reset&&!fault&&!(compact&&canceled_rows);
 assign packet_length={head_length[8]&&!compact,head_length[7:0]};
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};for(j=0;j<8;j=j+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 function automatic [7:0] crc8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end
 endfunction
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck,miso_hold,can_write;
 reg [2:0] bit_count;reg [8:0] byte_count;
 reg [7:0] shift,command,payload_size;reg payload_high;reg [15:0] request_crc,received_crc;
 reg [135:0] snapshot;reg [7:0] reply,status_crc;
 reg stop_at_command;integer j;
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire ours=command==8'he0||command==8'he1;
 wire idle_receipt=enable&&!fault&&used==0&&ack_valid&&!checking;
 wire [7:0] flags={fault,3'd0,(progress&&idle_receipt),full,ack_valid,(used!=0)};
 wire [8:0] expected_length={1'b0,payload_size}+9'd16;
 wire [7:0] received_offset=byte_count[7:0]-8'd1;
 // Use the original transaction cursor for both raw and expanded slots.
 // At the last literal in each row, skip the 46 implicit bytes. The CRC is
 // still shifted only on actual incoming SPI bits.
 wire skip_tail=command==8'he1 && receiving_rows && byte_count[5:0]==34 && byte_count<=expected_length;
 assign selected=!reset&&!SPI_SS&&ours&&byte_count!=0;
 assign miso=miso_hold;
 always @*begin
  reply=0;
  if(command==8'he0)begin
   case(byte_count)
    1:reply=8'hf7;
    2:reply={snapshot[135:132],snapshot[131]&&!stop_at_command,snapshot[130:128]};
    3:reply=accepted[15:8];
    4:reply=accepted[7:0];
    5:reply=snapshot[111:104];
    6:reply=snapshot[103:96];
    7:reply=snapshot[95:88];
    8:reply=snapshot[87:80];
    9:reply=snapshot[79:72];
    10:reply=snapshot[71:64];
    11:reply=snapshot[63:56];
    12:reply=snapshot[55:48];
    13:reply=snapshot[47:40];
    14:reply=snapshot[39:32];
    15:reply=snapshot[31:24];
    16:reply=snapshot[23:16];
    17:reply=snapshot[15:8];
    18:reply=snapshot[7:0];
    19:reply=status_crc;
    default:reply=0;
   endcase
   if(byte_count>=7 && byte_count<=18 && !snapshot[129])reply=0;
  end
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   expected_read<=0;canceled_rows<=0;opcode_nine<=0;receiving_rows<=0;
   progress<=0;accepted<=0;retired<=0;ack_work<=0;ack_mask<=0;ack_valid<=0;fault<=0;
   checking<=0;compare_pending<=0;compare_index<=0;compare_byte<=0;
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;can_write<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;payload_size<=0;payload_high<=0;
   request_crc<=16'hffff;received_crc<=0;snapshot<=0;status_crc<=0;stop_at_command<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(stop)canceled_rows<=1;
   if(enable && !fault && used!=0 && compact) begin
    if(stop||canceled_rows) fault<=1;
    if(completed_read) begin
     if(!completed_valid || !packet_ready || completed_address!=expected_read || {1'b0,expected_read}>=packet_length)
      fault<=1;
     else expected_read<=expected_read+1'b1;
    end
   end
   if(map_progress&&!stop&&idle_receipt)progress<=1;
   if(!enable||stop||fault||ack_write||ack_publish)progress<=0;
   compare_pending<=ack_write&&packet_ready&&ack_index<12;
   if(ack_write)begin compare_index<=ack_index;compare_byte<=ack_byte;end
   if(compare_pending)ack_mask[compare_index]<=compare_ok;
   if(ack_write&&enable&&!fault)begin
    if(!packet_ready||ack_index>=12||ack_publish)fault<=1;
    // ACK bytes become invalid as soon as the next response is written.
    // Nonempty queue retains cumulative retired credit, not its old ACK.
    else begin ack_valid<=0;ack_work[ack_index*8+:8]<=ack_byte;end
   end
   if(ack_publish&&enable&&!fault)begin
    if(!packet_ready || ack_write || (compact && {1'b0,expected_read}!=packet_length))fault<=1;
    else checking<=1;
   end
   // Delay commit for the synchronous comparator, including a publish directly
   // following the last byte. A failed comparison can never release credit.
   if(checking&&enable&&!fault)begin
    checking<=0;
    if(ack_mask!=12'hfff || ack_write || ack_publish || (compact&&(stop||canceled_rows||completed_read)))begin fault<=1;ack_valid<=1;end
    else begin
     expected_read<=0;
     if(compact)ack_work[15:8]<=9;
     retired<=retired+1'b1;ack_valid<=1;ack_mask<=0;
    end
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bit_count];
   if(ss[1])begin
    opcode_nine<=0;receiving_rows<=0;bit_count<=0;byte_count<=0;command<=0;miso_hold<=0;request_crc<=16'hffff;payload_size<=0;payload_high<=0;received_crc<=0;
    if(!prev_ss&&ours)begin
     if(command==8'he0)begin if(byte_count!=20||bit_count!=0)fault<=1;end
     else if(!can_write||!enable||fault||payload_high||(receiving_rows && (stop||canceled_rows))||payload_size>240||byte_count!=expected_length+3||bit_count!=0||received_crc!=request_crc)fault<=1;
     else begin progress<=0;accepted<=accepted+1'b1;end
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(command==8'he1 && byte_count!=0 && (byte_count<=14 || byte_count<=expected_length))
     request_crc<={request_crc[14:0],1'b0} ^ ((request_crc[15]^mosi[1])?16'h1021:16'h0000);
    // MISO was registered on the preceding falling edge. Include F7 via the
    // initial seed and the following 17 bytes one transmitted bit at a time.
    if(command==8'he0 && byte_count>=2 && byte_count<=18)
     status_crc<={status_crc[6:0],1'b0} ^ ((status_crc[7]^miso_hold)?8'h07:8'h00);
    if(bit_count==7)begin
     if(skip_tail)byte_count<={byte_count[8:6]+3'd1,6'd17};
     else if(byte_count!=511)byte_count<=byte_count+1'b1;
     if(byte_count==0)begin
      command<=incoming;can_write<=enable&&!full&&!fault;
      request_crc<=crc16(16'hffff,8'he1);
      snapshot[135:128]<=flags;
      snapshot[111:96]<=retired;
      status_crc<=crc8(8'd0,8'hf7);stop_at_command<=stop;
      for(j=0;j<12;j=j+1)snapshot[95-j*8-:8]<=ack_work[j*8+:8];
     end else if(command==8'he1)begin
      if(byte_count==1)opcode_nine<=incoming==9;
      if(byte_count==2)receiving_rows<=opcode_nine&&incoming==2;
      if(receiving_rows && byte_count==11 && |incoming[5:0])fault<=1;
      if(byte_count==13)begin
       payload_size<=receiving_rows?{incoming[2:1],6'b0}:incoming;
       if(receiving_rows && !(incoming==18 || incoming==36 || incoming==54))fault<=1;
      end
      if(byte_count==14)begin
       payload_high<=incoming!=0;
       // Only the free E1 slot is writable. CRC and STOP still gate publication.
       if(can_write)lengths[accepted[1:0]]<={receiving_rows|expected_length[8],expected_length[7:0]};
      end
      if(byte_count<=14||byte_count<=expected_length)begin

       if(can_write&&byte_count<=256)buffer[{accepted[1:0],received_offset}]<=receiving_rows && byte_count==13?{incoming[2:1],6'b0}:incoming;
      end else if(byte_count==expected_length+1)received_crc[15:8]<=incoming;
      else if(byte_count==expected_length+2)received_crc[7:0]<=incoming;
     end
    end
   end
  end
 end
endmodule
