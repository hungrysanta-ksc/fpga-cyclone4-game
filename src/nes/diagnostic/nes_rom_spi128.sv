// SPDX-License-Identifier: MIT
//128: validate a complete frame, then retire one memory clock later.
// CHECK/read/ack/finish retains protocol0x59. New frames during retirement fail closed.
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
 // ACKs are separated by complete SPI frames. Precompute the low-byte carry
 // to avoid a17-bit increment chain on the command retirement edge.
 reg next_carry8;
 always @(posedge mem_clk or posedge reset)
  if(reset)next_carry8<=0;else next_carry8<=&check_next[7:0];
 reg [7:0] checked_data;
 assign check_address=check_next;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] ss_sync,sck_sync,mosi_sync;
 reg ss_previous,sck_previous,miso_hold;
 reg [2:0] bit_count;
 reg [3:0] byte_count;
 reg [7:0] shift,command,arg,arg_not,received_crc,tail,crc;
 reg [23:0] offset;
 reg offset_matches_next,next_below_length,next_matches_length;
 always @(posedge mem_clk or posedge reset)
  if(reset)begin offset_matches_next<=0;next_below_length<=0;next_matches_length<=0;end
  else begin
   offset_matches_next <= offset=={7'd0,check_next};
   next_below_length <= check_next<loaded_bytes;
   next_matches_length <= check_next==loaded_bytes;
  end
 // Framing and lifecycle checks are captured in parallel; effects are delayed.
 reg pending;reg [3:0] pending_command,pending_header_error,pending_body_error;
 reg [7:0] pending_arg;
 reg [3:0] body_error;
 always @* begin
  body_error=0;
  case(command)
   8'h60:if(offset!=0)body_error=5;else if(check_enable)body_error=6;
   8'h61:if(offset!={7'd0,loaded_bytes})body_error=5;else if(check_enable)body_error=6;else if(!load_ready)body_error=4;
   8'h62:if(offset!={7'd0,loaded_bytes})body_error=5;else if(check_enable)body_error=6;
   8'h63:if(offset!={7'd0,loaded_bytes})body_error=5;else if(check_enable)body_error=6;else if(!verified || !loaded || run_enable)body_error=8;
   8'h64:if(offset!={7'd0,loaded_bytes})body_error=5;
   8'h65,8'h6a:;
   8'h66:if(!loaded || run_enable || check_enable || offset!=0)body_error=6;
   8'h67:if(!check_enable || check_busy || check_done || !check_ready || !offset_matches_next || !next_below_length)body_error=6;
   8'h68:if(!check_enable || check_busy || !check_done || !offset_matches_next || arg!=checked_data)body_error=8;
   8'h69:if(!check_enable || check_busy || check_done || !next_matches_length || offset!={7'd0,loaded_bytes})body_error=8;
   default:body_error=3;
  endcase
 end
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
   pending<=0;pending_command<=0;pending_arg<=0;pending_header_error<=0;pending_body_error<=0;
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
   pending<=0;
   if(!fault)begin
    // Hard faults win over a queued command; never release RUN on the same edge.
    if(check_fault || (check_enable && boot_fault))fail(9);
    else if(check_response && (!check_enable || !check_busy || check_response_address!=check_next))fail(7);
    else if(pending && !ss_sync[1])fail(1);
    else begin
     if(check_response)begin checked_data<=check_data;check_busy<=0;check_done<=1;end
     if(pending)begin
      if(pending_header_error!=0)fail(pending_header_error);
      else if(pending_body_error!=0)fail(pending_body_error);
      else case(pending_command)
       4'h0:begin load_begin<=1;load_chr32<=pending_arg[0];verified<=0;check_next<=0;end
       4'h1:begin load_valid<=1;load_data<=pending_arg;end
       4'h2:load_end<=1;
       4'h3:start<=1;
       4'h4:begin stop<=1;check_enable<=0;check_busy<=0;check_done<=0;verified<=0;check_next<=0;end
       4'h6:begin check_enable<=1;check_busy<=0;check_done<=0;verified<=0;check_next<=0;end
       4'h7:begin check_request<=1;check_busy<=1;end
       4'h8:begin check_done<=0;check_next[7:0]<=check_next[7:0]+1'b1;check_next[16:8]<=check_next[16:8]+next_carry8;end
       4'h9:begin check_enable<=0;verified<=1;end
       default:;
      endcase
     end
    end
   end
   // A complete coherent status snapshot is held for this transaction.
   if(!ss_sync[1] && !sck_sync[1] && sck_previous)miso_hold<=reply[7-bit_count];
   if(ss_sync[1])begin
    miso_hold<=0;bit_count<=0;byte_count<=0;crc<=0;command<=0;
    if(!ss_previous && ours && !fault && !pending)begin
     pending<=1;pending_command<=command[3:0];pending_arg<=arg;
     if(byte_count!=8 || bit_count!=0)pending_header_error<=1;
     else if(crc!=received_crc || tail!=8'ha5 || arg_not!=~arg)pending_header_error<=2;
     else if(command>8'h6a || (command!=8'h61 && command!=8'h68 && ((command==8'h60)?arg>1:arg!=0)))pending_header_error<=3;
     else pending_header_error<=0;
     pending_body_error<=body_error;
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
