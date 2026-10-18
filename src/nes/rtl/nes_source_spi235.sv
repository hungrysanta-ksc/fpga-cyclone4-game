// SPDX-License-Identifier: MIT
// Candidate N4 record -> two immutable blocks -> SPI D0/D1/D2/D3.
// One512x8 dual-clock RAM. Common reset is mandatory; no independent resets.
// Block POP is not source COMMIT or final SNES DISPLAYED acknowledgement.
module nes_source_spi235(
 input wire src_clk,host_clk,reset,abort_source,
 input wire record_valid,output wire record_ready,input wire [7:0] record_length,
 input wire record_flush,input wire byte_valid,output wire byte_ready,input wire [7:0] byte_data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output wire ack_valid,input wire ack_ready,output wire ack_accept,output wire [15:0] ack_generation,
 output wire source_fault,host_fault
);
 (* ramstyle="M9K" *) reg [7:0] memory[0:511];
 (* async_reg="true" *) reg [1:0] sr,hr,hfault_sync,sfault_sync,host_up_sync;
 always @(posedge src_clk or posedge reset)if(reset)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge host_clk or posedge reset)if(reset)hr<=0;else hr<={hr[0],1'b1};
 wire src_reset=!sr[1],host_reset=!hr[1];
 reg sfault,hfault,bank,flush_record;
 reg [1:0] busy,sent,publish;
 reg [7:0] used,remaining;
 reg [15:0] block_crc;
 reg [23:0] descriptor0,descriptor1;
 wire [1:0] pub_ready,block_valid;wire [23:0] block0,block1;
 reg pop0,pop1;
 nes_native_mailbox206 #(.WIDTH(24)) desc0(src_clk,host_clk,reset,publish[0],pub_ready[0],descriptor0,block_valid[0],pop0,block0);
 nes_native_mailbox206 #(.WIDTH(24)) desc1(src_clk,host_clk,reset,publish[1],pub_ready[1],descriptor1,block_valid[1],pop1,block1);
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};for(j=0;j<8;j=j+1)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 assign source_fault=sfault||hfault_sync[1];assign host_fault=hfault||sfault_sync[1];
 wire source_live=sr[1]&&host_up_sync[1]&&!source_fault&&!abort_source;
 wire room={1'b0,used}+{1'b0,record_length}<=248;
 assign record_ready=source_live&&!busy[bank]&&!remaining&&record_length!=0&&record_length<=243&&room;
 assign byte_ready=source_live&&!busy[bank]&&remaining!=0;
 // No RAM reset. Unpublished/partial data is never visible to the reader.
 always @(posedge src_clk)if(byte_valid&&byte_ready)memory[{bank,used}]<=byte_data;
 task seal(input [7:0] length,input [15:0] checksum);
  begin
   if(bank)descriptor1<={length,checksum};else descriptor0<={length,checksum};
   publish[bank]<=1;busy[bank]<=1;bank<=~bank;used<=0;block_crc<=16'hffff;
  end
 endtask
 integer i;
 always @(posedge src_clk or posedge src_reset)begin
  if(src_reset)begin
   hfault_sync<=0;host_up_sync<=0;sfault<=0;bank<=0;busy<=0;sent<=0;publish<=0;used<=0;remaining<=0;
   block_crc<=16'hffff;descriptor0<=0;descriptor1<=0;flush_record<=0;
  end else begin
   hfault_sync<={hfault_sync[0],hfault};host_up_sync<={host_up_sync[0],hr[1]};
   if(abort_source)sfault<=1;
   for(i=0;i<2;i=i+1)begin
    if(publish[i]&&pub_ready[i])begin publish[i]<=0;sent[i]<=1;end
    if(busy[i]&&sent[i]&&pub_ready[i])begin busy[i]<=0;sent[i]<=0;end
   end
   if(source_live)begin
    if(record_valid&&!remaining&&!busy[bank])begin
     if(!record_length||record_length>243)sfault<=1;
     else if(!room)begin if(!used)sfault<=1;else seal(used,block_crc);end
     else begin remaining<=record_length;flush_record<=record_flush;end
    end
    if(byte_valid&&byte_ready)begin
     remaining<=remaining-1'b1;used<=used+1'b1;block_crc<=c16(block_crc,byte_data);
     if(remaining==1&&(flush_record||used==247))seal(used+1'b1,c16(block_crc,byte_data));
    end
   end
  end
 end

 reg read_bank,read_seen,reading;
 reg [15:0] token;
 wire sealed=block_valid[read_bank];
 wire [23:0] descriptor=read_bank?block1:block0;
 wire [7:0] length=descriptor[23:16];wire [15:0] checksum=descriptor[15:0];
 reg ack_pending;wire ack_send_ready,ack_received;reg [16:0] ack_data;wire [16:0] ack_out;
 nes_native_mailbox206 #(.WIDTH(17)) prepared(host_clk,src_clk,reset,ack_pending,ack_send_ready,ack_data,ack_received,ack_ready&&source_live,ack_out);
 assign ack_valid=ack_received&&source_live;
 assign ack_accept=ack_out[16];assign ack_generation=ack_out[15:0];
 (* async_reg="true" *) reg [1:0] ss,sck,mosi;
 reg prev_ss,prev_sck,miso_hold;
 reg [2:0] bit_count;reg [8:0] byte_count;
 reg [7:0] read_byte,shift,command,arg,arg_not,received_crc,tail,request_crc;
 reg [23:0] offset;reg [55:0] snapshot;
 wire [7:0] read_address=byte_count[7:0]-1'b1;
 always @(posedge host_clk)read_byte<=memory[{read_bank,read_address}];
 wire [7:0] incoming={shift[6:0],mosi[1]};
 wire ours=command>=8'hd0&&command<=8'hd3;
 assign selected=hr[1]&&!SPI_SS&&ours&&byte_count!=0;assign miso=miso_hold;
 wire ack_available=!ack_pending&&ack_send_ready;
 wire [7:0] flags={host_fault,5'd0,ack_available,sealed};
 // D8 distinguishes this N4 byte transport from old D6 tagged-record SPI.
 wire [7:0] status_crc=c8(c8(c8(c8(c8(c8(0,8'hd8),flags),token[15:8]),token[7:0]),0),length);
 reg [7:0] reply;
 always @*begin
  reply=0;
  if(command==8'hd1&&reading)begin
   if(byte_count>=1&&byte_count<={1'b0,length})reply=read_byte;
   else if(byte_count=={1'b0,length}+1)reply=checksum[15:8];
   else if(byte_count=={1'b0,length}+2)reply=checksum[7:0];
  end else case(byte_count)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];
   4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];7:reply=snapshot[7:0];default:;
  endcase
 end
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin
   sfault_sync<=0;hfault<=0;read_bank<=0;read_seen<=0;reading<=0;token<=0;pop0<=0;pop1<=0;
   ack_pending<=0;ack_data<=0;ss<=3;sck<=0;mosi<=0;prev_ss<=1;prev_sck<=0;miso_hold<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;arg<=0;arg_not<=0;received_crc<=0;
   tail<=0;request_crc<=0;offset<=0;snapshot<=0;
  end else begin
   sfault_sync<={sfault_sync[0],sfault};pop0<=0;pop1<=0;
   if(ack_pending&&ack_send_ready)ack_pending<=0;
   ss<={ss[0],SPI_SS};sck<={sck[0],SPI_SCK};mosi<={mosi[0],SPI_MOSI};prev_ss<=ss[1];prev_sck<=sck[1];
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bit_count];
   if(ss[1])begin
    bit_count<=0;byte_count<=0;request_crc<=0;command<=0;miso_hold<=0;
    if(!prev_ss&&ours)begin
     if(command==8'hd1)begin
      if(!host_fault&&reading&&byte_count=={1'b0,length}+3&&bit_count==0)read_seen<=1;
      else begin read_seen<=0;hfault<=1;end
     end else if(byte_count!=8||bit_count!=0||received_crc!=request_crc||tail!=8'ha5||arg_not!=~arg)hfault<=1;
     else case(command)
      8'hd0:if(offset!=0||arg!=0)hfault<=1;
      8'hd2:if(host_fault||!sealed||!read_seen||offset!={8'd0,token}||arg!=0||token==16'hffff)hfault<=1;
       else begin
        if(read_bank)pop1<=1;else pop0<=1;
        read_bank<=~read_bank;read_seen<=0;token<=token+1'b1;
       end
      8'hd3:if(host_fault||offset[23:16]!=0||arg>1||!ack_available)hfault<=1;
       else begin ack_pending<=1;ack_data<={arg[0],offset[15:0]};end
      default:;
     endcase
    end
   end else if(sck[1]&&!prev_sck)begin
    shift<=incoming;bit_count<=bit_count+1'b1;
    if(bit_count==7)begin
     if(byte_count!=511)byte_count<=byte_count+1'b1;
     if(byte_count<6)request_crc<=c8(request_crc,incoming);
     case(byte_count)
      0:begin command<=incoming;reading<=sealed&&!host_fault;snapshot<={8'hd8,flags,token,8'd0,length,status_crc};if(incoming==8'hd1)read_seen<=0;end
      1:offset[23:16]<=incoming;2:offset[15:8]<=incoming;3:offset[7:0]<=incoming;
      4:arg<=incoming;5:arg_not<=incoming;6:received_crc<=incoming;7:tail<=incoming;default:;
     endcase
    end
   end
  end
 end
endmodule
