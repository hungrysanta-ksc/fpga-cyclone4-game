// SPDX-License-Identifier: MIT
// Host-clock single256-byte block. Mode0 command range D0..D3 only.
// D0=status8, D1=read(length+3), D2=pop8, D3=prepared8.
module nes_native_spi165(
 input wire clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,output wire miso,
 input wire record_valid,output wire record_ready,input wire [95:0] record_data,
 output reg ack_valid,input wire ack_ready,output reg ack_accept,output reg [15:0] ack_generation,
 output reg fault
);
 reg [7:0] buffer[0:255];reg [8:0] used;reg [15:0] token,block_crc;
 reg sealed,encoding,read_seen;reg [95:0] held;reg [3:0] position,total;
 function automatic [3:0] width(input [2:0] kind);
  case(kind)0:width=2;1,5:width=1;2,4:width=7;3:width=3;6:width=2;default:width=8;endcase
 endfunction
 function automatic [15:0] crc16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};for(j=0;j<8;j=j+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 function automatic [7:0] crc8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;crc8=c;end
 endfunction
 wire [15:0] tag={held[95:93],held[76:64]};reg [7:0] pack_byte;
 always @*case(position)
  0:pack_byte=tag[15:8];1:pack_byte=tag[7:0];2:pack_byte=held[92:85];3:pack_byte=held[84:77];
  default:pack_byte=held[63:0]>>((total-1-position)*8);
 endcase
 assign record_ready=!reset&&!sealed&&!encoding&&used<=244;
 (* async_reg="true" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck,miso_hold;reg [2:0] bit_count;reg [8:0] byte_count;
 reg [7:0] shift,command,arg,arg_not,received_crc,tail,request_crc;
 reg [23:0] offset;reg reading;reg [55:0] snapshot;reg [7:0] reply;
 wire [7:0] incoming={shift[6:0],mosi[1]};wire ours=command>=8'hd0&&command<=8'hd3;
 assign selected=!reset&&!SPI_SS&&ours&&byte_count!=0;assign miso=miso_hold;
 wire [7:0] flags={fault,5'd0,!ack_valid,sealed};
 reg [7:0] status_crc;
 always @* begin
  status_crc=crc8(crc8(crc8(crc8(crc8(crc8(0,8'hd6),flags),token[15:8]),token[7:0]),{7'd0,used[8]}),used[7:0]);
  reply=0;
  if(command==8'hd1&&reading)begin
   if(byte_count>=1&&byte_count<=used)reply=buffer[byte_count-1];
   else if(byte_count==used+1)reply=block_crc[15:8];
   else if(byte_count==used+2)reply=block_crc[7:0];
  end else case(byte_count)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];4:reply=snapshot[31:24];
   5:reply=snapshot[23:16];6:reply=snapshot[15:8];7:reply=snapshot[7:0];default:reply=0;
  endcase
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   used<=0;token<=0;block_crc<=16'hffff;sealed<=0;encoding<=0;held<=0;position<=0;total<=0;read_seen<=0;
   ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;bit_count<=0;byte_count<=0;shift<=0;command<=0;
   arg<=0;arg_not<=0;received_crc<=0;tail<=0;request_crc<=0;offset<=0;reading<=0;snapshot<=0;
   ack_valid<=0;ack_accept<=0;ack_generation<=0;fault<=0;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(ack_valid&&ack_ready)ack_valid<=0;
   if(record_valid&&record_ready)begin held<=record_data;position<=0;total<=4+width(record_data[95:93]);encoding<=1;end
   if(encoding)begin
    buffer[used]<=pack_byte;used<=used+1'b1;block_crc<=crc16(block_crc,pack_byte);
    if(position+1==total)begin
     encoding<=0;
     if(used+1>244 || (held[95:93]==7&&held[76:64]!=0))sealed<=1;
    end else position<=position+1'b1;
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bit_count];
   if(ss[1])begin
    bit_count<=0;byte_count<=0;request_crc<=0;command<=0;miso_hold<=0;
    if(!prev_ss&&ours)begin
     if(command==8'hd1)begin
      if(reading&&byte_count==used+3&&bit_count==0)read_seen<=1;
      else begin read_seen<=0;fault<=1;end
     end else if(byte_count!=8||bit_count!=0||received_crc!=request_crc||tail!=8'ha5||arg_not!=~arg)fault<=1;
     else case(command)
      8'hd0:if(offset!=0||arg!=0)fault<=1;
      8'hd2:if(!sealed||!read_seen||offset!={8'd0,token}||arg!=0)fault<=1;
       else begin sealed<=0;read_seen<=0;used<=0;block_crc<=16'hffff;token<=token+1'b1;end
      8'hd3:if(offset[23:16]!=0||arg>1||ack_valid)fault<=1;
       else begin ack_valid<=1;ack_accept<=arg[0];ack_generation<=offset[15:0];end
      default:;
     endcase
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=511)byte_count<=byte_count+1'b1;
     if(byte_count<6)request_crc<=crc8(request_crc,incoming);
     case(byte_count)
      0:begin command<=incoming;reading<=sealed;snapshot<={8'hd6,flags,token,7'd0,used,status_crc};if(incoming==8'hd1)read_seen<=0;end
      1:offset[23:16]<=incoming;2:offset[15:8]<=incoming;3:offset[7:0]<=incoming;
      4:arg<=incoming;5:arg_not<=incoming;6:received_crc<=incoming;7:tail<=incoming;default:;
     endcase
    end
   end
  end
 end
endmodule
