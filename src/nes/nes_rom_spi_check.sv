// SPDX-License-Identifier: MIT
// 059 extends054 framing with ordered CHECK/read/ack/finish, protocol0x59.
// MCU compares actual response bytes with its approved image before ACK.
// This is a lifecycle gate, not authentication against a malicious MCU.
module nes_rom_spi_check(
 input wire mem_clk,reset,SPI_SS,SPI_SCK,SPI_MOSI,
 output wire spi_miso,spi_selected,
 input wire load_ready,loaded,run_enable,boot_fault,
 input wire [3:0] boot_error,input wire [16:0] loaded_bytes,
 output reg load_begin,load_chr32,load_valid,load_end,start,stop,
 output reg [7:0] load_data,output reg fault,output reg [3:0] error_code,
 output reg check_enable,check_request,output wire [16:0] check_address,
 input wire check_ready,check_response,check_fault,
 input wire [16:0] check_response_address,input wire [7:0] check_data);
 reg check_busy,check_done,verified;
 reg [16:0] check_next;
 reg [7:0] checked_data;
 assign check_address=check_next;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss_sync,sck_sync,mosi_sync;
 reg ss_previous,sck_previous,miso_hold;
 reg [2:0] bit_count;
 reg [3:0] byte_count;
 reg [7:0] shift,command,arg,arg_not,received_crc,tail,crc;
 reg [23:0] offset;
 reg [55:0] snapshot;
 wire ours=command[7:4]==4'h6;
 assign spi_selected=!reset && !SPI_SS && ours && byte_count!=0;
 assign spi_miso=miso_hold;
 function automatic [7:0] crc_byte(input [7:0] previous,input [7:0] value);
  reg [7:0] c;integer i;begin
   c=previous^value;
   for(i=0;i<8;i=i+1)c=c[7]?(c<<1)^8'h07:(c<<1);
   crc_byte=c;
  end
 endfunction
 wire [7:0] incoming={shift[6:0],mosi_sync[1]};
 wire [7:0] flags={verified,check_done,check_enable,boot_fault,fault,run_enable&&!fault,loaded&&!fault,
                   check_enable?check_busy:(load_ready&&!fault)};
 reg [7:0] reply;
 always @* begin
  case(byte_count)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];
   4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];
   7:reply=snapshot[7:0];default:reply=0;
  endcase
 end
 task automatic fail(input [3:0] code);begin
  fault<=1;error_code<=code;check_enable<=0;check_busy<=0;check_done<=0;verified<=0;
 end endtask
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin
   ss_sync<=3;sck_sync<=0;mosi_sync<=0;ss_previous<=1;sck_previous<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;arg<=0;arg_not<=0;
   received_crc<=0;tail<=0;crc<=0;offset<=0;snapshot<=0;miso_hold<=0;
   load_begin<=0;load_chr32<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;
   load_data<=0;fault<=0;error_code<=0;
   check_enable<=0;check_request<=0;check_busy<=0;check_done<=0;verified<=0;check_next<=0;checked_data<=0;
  end else begin
   ss_sync<={ss_sync[0],SPI_SS};sck_sync<={sck_sync[0],SPI_SCK};mosi_sync<={mosi_sync[0],SPI_MOSI};
   ss_previous<=ss_sync[1];sck_previous<=sck_sync[1];
   load_begin<=0;load_valid<=0;load_end<=0;start<=0;stop<=0;
   check_request<=0;
   if(!fault)begin
    if(check_fault || (check_enable && boot_fault))fail(9);
    else if(check_response)begin
     if(!check_enable || !check_busy || check_response_address!=check_next)fail(7);
     else begin checked_data<=check_data;check_busy<=0;check_done<=1;end
    end
   end
   // A complete coherent status snapshot is held for this transaction.
   if(!ss_sync[1] && !sck_sync[1] && sck_previous)miso_hold<=reply[7-bit_count];
   if(ss_sync[1])begin
    miso_hold<=0;bit_count<=0;byte_count<=0;crc<=0;command<=0;
    if(!ss_previous && ours && !fault)begin
     if(byte_count!=8 || bit_count!=0)fail(1);
     else if(crc!=received_crc || tail!=8'ha5 || arg_not!=~arg)fail(2);
     else if(command>8'h6a || (command!=8'h61 && command!=8'h68 && ((command==8'h60)?arg>1:arg!=0)))fail(3);
     else if(command==8'h65 || command==8'h6a)begin end
     else if(command>=8'h66)begin
      case(command)
       8'h66:if(!loaded || run_enable || check_enable || offset!=0)fail(6);
        else begin check_enable<=1;check_busy<=0;check_done<=0;verified<=0;check_next<=0;end
       8'h67:if(!check_enable || check_busy || check_done || !check_ready ||
                  offset!={7'd0,check_next} || check_next>=loaded_bytes)fail(6);
        else begin check_request<=1;check_busy<=1;end
       8'h68:if(!check_enable || check_busy || !check_done || offset!={7'd0,check_next} || arg!=checked_data)fail(8);
        else begin check_done<=0;check_next<=check_next+1'b1;end
       8'h69:if(!check_enable || check_busy || check_done || check_next!=loaded_bytes || offset!={7'd0,loaded_bytes})fail(8);
        else begin check_enable<=0;verified<=1;end
       default:fail(3);
      endcase
     end
     else if((command==8'h60 && offset!=0) || (command!=8'h60 && offset!={7'd0,loaded_bytes}))fail(5);
     else if(check_enable && command!=8'h64)fail(6);
     else case(command)
      8'h60:begin load_begin<=1;load_chr32<=arg[0];verified<=0;check_next<=0;end
      8'h61:if(!load_ready)fail(4);else begin load_valid<=1;load_data<=arg;end
      8'h62:load_end<=1;
      8'h63:if(!verified)fail(8);else start<=1;
      8'h64:begin stop<=1;check_enable<=0;check_busy<=0;check_done<=0;verified<=0;check_next<=0;end
      default:fail(3);
     endcase
    end
   end else if(sck_sync[1] && !sck_previous)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=9)byte_count<=byte_count+1'b1;
     if(byte_count<6)crc<=crc_byte(crc,incoming);
     case(byte_count)
      0:begin command<=incoming;
       if(incoming==8'h6a)snapshot<={8'h59,flags,checked_data,7'd0,check_next,error_code,boot_error};
       else snapshot<={8'h59,flags,{4'd0,error_code},7'd0,loaded_bytes,{4'd0,boot_error}};
      end
      1:offset[23:16]<=incoming;2:offset[15:8]<=incoming;3:offset[7:0]<=incoming;
      4:arg<=incoming;5:arg_not<=incoming;6:received_crc<=incoming;7:tail<=incoming;
      default:;
     endcase
    end
   end
  end
 end
endmodule
