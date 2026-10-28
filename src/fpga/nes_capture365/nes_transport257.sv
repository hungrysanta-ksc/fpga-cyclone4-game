// SPDX-License-Identifier: MIT
// Candidate N4 record -> two immutable blocks -> SPI D0/D1/D2/D3.
// One512x8 dual-clock RAM. Common reset is mandatory; no independent resets.
// Block POP is not source COMMIT or final SNES DISPLAYED acknowledgement.
module nes_transport257(input wire record_last319,
 input wire [113:0] link270,output wire [199:0] status270,output wire crc_take270,


 input wire [15:0] crc_result,output reg crc_pending,
 output wire [15:0] crc_previous,output reg [7:0] crc_byte,
 input wire [15:0] frame_generation,
 input wire src_clk,host_clk,reset,abort_source,
 input wire record_valid,output wire record_ready,input wire [7:0] record_length,
 input wire record_flush,input wire byte_valid,output wire byte_ready,input wire [7:0] byte_data,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 output wire ack_valid,input wire ack_ready,output wire ack_accept,output wire [15:0] ack_generation,
 output wire source_fault,host_fault,source_empty
);
 (* ramstyle="M9K" *) reg [7:0] memory[0:511];
 (* async_reg="true" *) reg [1:0] sr,hr,hfault_sync,sfault_sync,host_up_sync;
 always @(posedge src_clk or posedge reset)if(reset)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge host_clk or posedge reset)if(reset)hr<=0;else hr<={hr[0],1'b1};
 wire src_reset=!sr[1],host_reset=!hr[1];
 reg sfault,hfault,bank,flush_record;
 reg [1:0] busy,sent,publish;
 reg [7:0] used;reg record_open319;
 reg [15:0] block_crc;
 reg [39:0] descriptor0,descriptor1;
 wire [1:0] pub_ready,block_valid;wire [39:0] block0,block1;
 reg pop0,pop1;
 nes_native_mailbox206 #(.WIDTH(40)) desc0(src_clk,host_clk,reset,publish[0],pub_ready[0],descriptor0,block_valid[0],pop0,block0);
 nes_native_mailbox206 #(.WIDTH(40)) desc1(src_clk,host_clk,reset,publish[1],pub_ready[1],descriptor1,block_valid[1],pop1,block1);
 assign source_fault=sfault||hfault_sync[1];assign host_fault=hfault||sfault_sync[1];
 wire source_live=sr[1]&&host_up_sync[1]&&!source_fault&&!abort_source;
 assign source_empty=source_live&&!busy&&!record_open319&&!used&&!crc_pending;
 assign crc_previous=block_crc;
 wire room={1'b0,used}+{1'b0,record_length}<=248;
 assign record_ready=source_live&&!crc_pending&&!busy[bank]&&!record_open319&&record_length!=0&&record_length<=243&&room;
 assign byte_ready=source_live&&!crc_pending&&!busy[bank]&&record_open319;
 // No RAM reset. Unpublished/partial data is never visible to the reader.
 always @(posedge src_clk)if(byte_valid&&byte_ready)memory[{bank,used}]<=byte_data;
 task seal(input [7:0] length,input [15:0] checksum);
  begin
   if(bank)descriptor1<={frame_generation,length,checksum};else descriptor0<={frame_generation,length,checksum};
   publish[bank]<=1;busy[bank]<=1;bank<=~bank;used<=0;block_crc<=16'hffff;
  end
 endtask
 integer i;
 always @(posedge src_clk or posedge src_reset)begin
  if(src_reset)begin
   hfault_sync<=0;host_up_sync<=0;sfault<=0;bank<=0;busy<=0;sent<=0;publish<=0;used<=0;record_open319<=0;
   crc_pending<=0;crc_byte<=0;block_crc<=16'hffff;descriptor0<=0;descriptor1<=0;flush_record<=0;
  end else begin
   hfault_sync<={hfault_sync[0],hfault};host_up_sync<={host_up_sync[0],hr[1]};
   if(abort_source)sfault<=1;
   for(i=0;i<2;i=i+1)begin
    if(publish[i]&&pub_ready[i])begin publish[i]<=0;sent[i]<=1;end
    if(busy[i]&&sent[i]&&pub_ready[i])begin busy[i]<=0;sent[i]<=0;end
   end
   if(source_live)begin
    if(record_valid&&!record_open319&&!busy[bank]&&!crc_pending)begin
     if(!record_length||record_length>243)sfault<=1;
     else if(!room)begin if(!used)sfault<=1;else seal(used,block_crc);end
     else begin record_open319<=1;flush_record<=record_flush;end
    end
    if(byte_valid&&byte_ready)begin

     if(record_last319)record_open319<=0;used<=used+1'b1;crc_pending<=1;crc_byte<=byte_data;
    end
    if(crc_pending)begin
     crc_pending<=0;block_crc<=crc_result;
     if(!record_open319&&(flush_record||used==248))seal(used,crc_result);
    end
   end
  end
 end

 // Checked D4 prefix may retire the fully read preceding block, then takes
 // an immutable snapshot of the NEXT bank. D5 combines final POP/input ACK.
 // Neither operation retires SNES display ownership.
 reg read_bank,read_seen,reading,request_ok280;
 reg [15:0] token;
 wire sealed=block_valid[read_bank];
 wire [39:0] descriptor=read_bank?block1:block0;
 wire [7:0] length=descriptor[23:16];wire [15:0] checksum=descriptor[15:0];
 reg ack_pending;wire ack_send_ready,ack_received;reg [16:0] ack_data;wire [16:0] ack_out;
 nes_native_mailbox206 #(.WIDTH(17)) prepared(host_clk,src_clk,reset,ack_pending,ack_send_ready,ack_data,ack_received,ack_ready&&source_live,ack_out);
 assign ack_valid=ack_received&&source_live;
 assign ack_accept=ack_out[16];assign ack_generation=ack_out[15:0];
 wire [7:0] common_crc270,status_reply270,command,incoming;
 wire [9:0] count270;wire [2:0] bits270;wire [1:0] ss,sck;wire prev_ss,prev_sck;
 assign {common_crc270,status_reply270,command,incoming,count270,bits270,ss[1],sck[1],prev_ss,prev_sck}=link270[48:0];
 wire [15:0] request_generation=link270[106:91],request_token=link270[90:75];
 wire [7:0] request_flags=link270[74:67];
 wire request_crc_good=link270[66];
 wire ack_available=!ack_pending&&ack_send_ready;
 wire ours=command==8'hd4||command==8'hd5;
 assign selected=hr[1]&&!SPI_SS&&ours&&count270!=0;
 reg miso_hold;assign miso=miso_hold;
 reg [7:0] read_byte,header_crc;
 reg snapshot_ready;
 // The checked prefix selects a bank. Its mailbox stays immutable until POP.
 // Keep ready sampled: a bank published during an empty response is NOT read.
 wire [7:0] snapshot_length=snapshot_ready?length:8'd0;
 wire [15:0] snapshot_crc=checksum,snapshot_token=token;
 wire next_bank=read_bank^request_flags[0];
 wire [39:0] next_descriptor=next_bank?block1:block0;
 wire next_sealed=block_valid[next_bank];
 wire [7:0] read_address=count270[7:0]-8'd13;
 always @(posedge host_clk)read_byte<=memory[{read_bank,read_address}];
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j=j+1)c=c[7]?(c<<1)^8'h07:c<<1;c8=c;end
 endfunction
 reg [7:0] reply;
 wire [7:0] response_flags={5'b10101,host_fault,ack_available,snapshot_ready};
 always @*begin
  reply=0;
  case(count270)
   8:reply=response_flags;9:reply=snapshot_length;
   10:reply=snapshot_token[15:8];11:reply=snapshot_token[7:0];12:reply=header_crc;
   default:if(reading)begin
    if(count270>=13&&count270<13+snapshot_length)reply=read_byte;
    else if(count270==13+snapshot_length)reply=snapshot_crc[15:8];
    else if(count270==14+snapshot_length)reply=snapshot_crc[7:0];
   end
  endcase
 end
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin
   sfault_sync<=0;hfault<=0;read_bank<=0;read_seen<=0;reading<=0;token<=0;pop0<=0;pop1<=0;
   ack_pending<=0;ack_data<=0;miso_hold<=0;request_ok280<=0;
   snapshot_ready<=0;header_crc<=0;
  end else begin
   sfault_sync<={sfault_sync[0],sfault};pop0<=0;pop1<=0;
   if(abort_source)hfault<=1;
   if(ack_pending&&ack_send_ready)ack_pending<=0;
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bits270];
   if(ss[1])begin
    miso_hold<=0;
    if(!prev_ss&&ours)begin
     if(!request_ok280||bits270!=0||
        count270!=(command==8'hd5 ? 10'd8:reading?15+snapshot_length:13))begin
      hfault<=1;read_seen<=0;
     end else if(command==8'hd4)read_seen<=reading;
    end
   end else if(sck[1]&&!prev_sck&&bits270==7)begin
    if(count270==0)begin request_ok280<=0;reading<=0;header_crc<=0;end
    if(ours&&count270==7)begin
     if(host_fault||!request_crc_good||incoming!=8'ha5||
       (command==8'hd4 ? request_flags>1:request_flags!=3)||
       (request_flags[0]&&(!sealed||!read_seen||request_token!=token||
          request_generation!=descriptor[39:24]||token==16'hffff))||
       (!request_flags[0]&&(read_seen||request_token!=token))||
       (next_sealed&&command==8'hd4&&next_descriptor[39:24]!=request_generation)||
       (command==8'hd5&&(!ack_available||next_sealed)))hfault<=1;
     else begin
      request_ok280<=1;read_seen<=0;
      if(request_flags[0])begin
       if(read_bank)pop1<=1;else pop0<=1;
       read_bank<=~read_bank;token<=token+1'b1;
      end
      if(command==8'hd5)begin ack_pending<=1;ack_data<={1'b1,request_generation};end
      else begin
       snapshot_ready<=next_sealed;
       reading<=next_sealed;
      end
     end
    end
    if(command==8'hd4&&count270>=8&&count270<=11)header_crc<=c8(header_crc,reply);
   end
  end
 end
 assign crc_take270=count270<6&&(count270==0?(incoming==8'hd4||incoming==8'hd5):ours);
 assign status270=0;


endmodule
