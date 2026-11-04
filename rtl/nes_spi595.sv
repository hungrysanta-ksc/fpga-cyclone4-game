// SPDX-License-Identifier: MIT
// Host-clock mode-0 input peripheral. Only a complete read may retire a page.
module nes_spi595(input wire clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 input wire seal,input wire [7:0] length,input wire end_raw,
 output wire [7:0] page_addr,input wire [7:0] page_byte,
 output reg event_valid,input wire event_ready,output wire [134:0] event_data,
 input wire toggle_async,source_fault_async,output reg fault);
 (* async_reg="true" *) reg [1:0] ss,sck,mosi,toggle,src_fault;
 reg old_ss,old_sck,sealed,read_seen,reading,prepare_ok,raw_page,hold_miso;
 reg [7:0] used,shift,cmd,arg,neg,crc8_rx,trailer,crc8_calc;
 reg [15:0] token,crc_read,crc_cmd,crc_rx;
 reg [2:0] bit_at;reg [8:0] byte_at;
 reg [23:0] offset;reg [55:0] snapshot;reg [7:0] reply;
 reg [127:0] payload;reg [6:0] action;reg fields_ok;
 wire [7:0] byte_in={shift[6:0],mosi[1]};
 wire ours=cmd>=8'hd0&&cmd<=8'hd4;
 wire [7:0] flags={fault||src_fault[1],4'd0,toggle[1],prepare_ok,sealed};
 assign selected=!reset&&!SPI_SS&&ours&&byte_at!=0;
 assign miso=hold_miso;
 assign page_addr=byte_at[7:0]-1'b1;
 assign event_data={action,payload};
 function automatic [7:0] c8(input [7:0] c,input [7:0] b);
  integer i;reg [7:0] t;begin t=c^b;for(i=0;i<8;i=i+1)t=t[7]?(t<<1)^7:t<<1;c8=t;end
 endfunction
 function automatic [15:0] c16(input [15:0] c,input [7:0] b);
  integer i;reg [15:0] t;begin t=c^{b,8'b0};for(i=0;i<8;i=i+1)t=t[15]?(t<<1)^16'h1021:t<<1;c16=t;end
 endfunction
 wire [7:0] status_crc=c8(c8(c8(c8(c8(c8(0,8'hd6),flags),token[15:8]),token[7:0]),0),used);
 always @*begin
  reply=0;
  if(cmd==8'hd1&&reading)begin
   if(byte_at<=used)reply=page_byte;
   else if(byte_at=={1'b0,used}+1)reply=crc_read[15:8];
   else if(byte_at=={1'b0,used}+2)reply=crc_read[7:0];
  end else case(byte_at)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];
   4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];7:reply=snapshot[7:0];default:;
  endcase
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   ss<=3;sck<=0;mosi<=0;old_ss<=1;old_sck<=0;toggle<=0;src_fault<=0;fault<=0;
   sealed<=0;read_seen<=0;used<=0;token<=0;prepare_ok<=0;event_valid<=0;
   bit_at<=0;byte_at<=0;cmd<=0;shift<=0;hold_miso<=0;reading<=0;
   crc_read<=16'hffff;crc_cmd<=16'hffff;crc8_calc<=0;fields_ok<=1;
  end else begin
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};old_ss<=ss[1];old_sck<=sck[1];
   toggle<={toggle[0],toggle_async};src_fault<={src_fault[0],source_fault_async};
   if(event_valid&&event_ready)event_valid<=0;
   if(seal)begin
    if(sealed||length<3||length>254)fault<=1;
    else begin sealed<=1;used<=length;raw_page<=end_raw;end
   end
   if(!ss[1]&&!sck[1]&&old_sck)hold_miso<=reply[7-bit_at];
   if(ss[1])begin
    bit_at<=0;byte_at<=0;cmd<=0;hold_miso<=0;crc8_calc<=0;crc_cmd<=16'hffff;fields_ok<=1;
    if(!old_ss&&ours&&!fault&&!src_fault[1])begin
     if(cmd==8'hd1)begin
      read_seen<=reading&&byte_at=={1'b0,used}+3&&bit_at==0;
      if(!reading||byte_at!={1'b0,used}+3||bit_at!=0)fault<=1;
     end else if(cmd==8'hd4)begin
      if(!fields_ok||crc_rx!=crc_cmd||byte_at!=24||bit_at!=0||event_valid||!event_ready||sealed||prepare_ok)fault<=1;
      else event_valid<=1;
     end else if(byte_at!=8||bit_at!=0||crc8_rx!=crc8_calc||trailer!=8'ha5||neg!=~arg)fault<=1;
     else case(cmd)
      8'hd0:if(offset!=0||arg!=0)fault<=1;
      8'hd2:if(!sealed||!read_seen||offset!={8'd0,token}||arg!=0||event_valid||!event_ready)fault<=1;
       else begin sealed<=0;used<=0;read_seen<=0;token<=token+1'b1;action<=5;payload[47:32]<=token;event_valid<=1;prepare_ok<=raw_page;end
      8'hd3:if(!prepare_ok||offset[23:16]!=0||arg!=1||event_valid||!event_ready)fault<=1;
       else begin prepare_ok<=0;action<=6;payload[63:48]<=offset[15:0];event_valid<=1;end
      default:;
     endcase
    end
   end else if(sck[1]&&!old_sck)begin
    shift<=byte_in;bit_at<=bit_at+1'b1;
    if(bit_at==7)begin
     if(byte_at<511)byte_at<=byte_at+1'b1;
     if(byte_at<6)crc8_calc<=c8(crc8_calc,byte_in);
     if(!byte_at)begin
      cmd<=byte_in;snapshot<={8'hd6,flags,token,8'd0,used,status_crc};reading<=sealed;
      if(byte_in==8'hd1)begin read_seen<=0;crc_read<=16'hffff;end
      if(byte_in==8'hd4)crc_cmd<=c16(16'hffff,byte_in);
     end else if(cmd==8'hd4)begin
      if(byte_at<20)crc_cmd<=c16(crc_cmd,byte_in);
      case(byte_at)
       1:fields_ok<=fields_ok && byte_in==1;
       2,3,4,5:payload[127:96]<={byte_in,payload[127:104]};
       6,7,8,9:payload[95:64]<={byte_in,payload[95:72]};
       10,11:payload[63:48]<={byte_in,payload[63:56]};
       12,13:payload[47:32]<={byte_in,payload[47:40]};
       14,15,16,17:payload[31:0]<={byte_in,payload[31:8]};
       18:begin action<=byte_in[6:0];fields_ok<=fields_ok && byte_in<=4;end
       19:fields_ok<=fields_ok && byte_in==0;
       20:crc_rx[7:0]<=byte_in;21:crc_rx[15:8]<=byte_in;
       22:fields_ok<=fields_ok && byte_in==8'h5a;23:fields_ok<=fields_ok && byte_in==8'ha5;
       default:;
      endcase
     end else if(cmd==8'hd1)begin if(byte_at<=used)crc_read<=c16(crc_read,page_byte);end
     else case(byte_at)
      1:offset[23:16]<=byte_in;2:offset[15:8]<=byte_in;3:offset[7:0]<=byte_in;
      4:arg<=byte_in;5:neg<=byte_in;6:crc8_rx<=byte_in;7:trailer<=byte_in;default:;
     endcase
    end
   end
  end
 end
endmodule
