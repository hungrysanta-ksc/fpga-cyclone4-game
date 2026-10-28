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
 // Four immutable packet slots, with six footer bytes in each 256-byte slot.
 // Gray pointers are the only packet ownership CDC; RAM is never reset.
 (* ramstyle="M9K" *) reg [7:0] memory[0:1023];
 (* async_reg="true" *) reg [1:0] sr,hr,hfault_sync,sfault_sync,host_up_sync;
 reg [2:0] wbin,wgray,rbin,rgray;
 (* async_reg="true" *) reg [2:0] rgray_s1,rgray_s2,wgray_h1,wgray_h2;
 function automatic [2:0] gray(input [2:0] b);begin gray=(b>>1)^b;end endfunction
 wire full=wgray=={~rgray_s2[2:1],rgray_s2[0]};
 wire empty=rgray==wgray_h2;
 always @(posedge src_clk or posedge reset)if(reset)sr<=0;else sr<={sr[0],1'b1};
 always @(posedge host_clk or posedge reset)if(reset)hr<=0;else hr<={hr[0],1'b1};
 wire src_reset=!sr[1],host_reset=!hr[1];
 reg sfault,hfault,flush_record,record_open319;
 reg [7:0] used,footer_length;reg [15:0] block_crc,footer_crc,footer_generation;
 reg footer_final;reg [2:0] footer_at;reg footer_busy;
 wire [3:0] publish=footer_busy&&footer_at==5?(4'b1<<wbin[1:0]):4'd0;
 assign source_fault=sfault||hfault_sync[1];assign host_fault=hfault||sfault_sync[1];
 wire source_live=sr[1]&&host_up_sync[1]&&!source_fault&&!abort_source;
 assign source_empty=source_live&&wgray==rgray_s2&&!record_open319&&!used&&!crc_pending&&!footer_busy;
 assign crc_previous=block_crc;
 wire room={1'b0,used}+{1'b0,record_length}<=248;
 assign record_ready=source_live&&!crc_pending&&!full&&!footer_busy&&!record_open319&&record_length!=0&&record_length<=243&&room;
 assign byte_ready=source_live&&!crc_pending&&!full&&!footer_busy&&record_open319;
 reg [7:0] footer_byte;
 always @*case(footer_at)
  0:footer_byte=footer_length;1:footer_byte={7'd0,footer_final};
  2:footer_byte=footer_generation[7:0];3:footer_byte=footer_generation[15:8];
  4:footer_byte=footer_crc[15:8];default:footer_byte=footer_crc[7:0];endcase
 always @(posedge src_clk)if(source_live)begin
  if(footer_busy)memory[{wbin[1:0],8'd250+{5'd0,footer_at}}]<=footer_byte;
  else if(byte_valid&&byte_ready)memory[{wbin[1:0],used}]<=byte_data;
 end
 task seal(input [15:0] checksum,input last_packet);
  begin footer_length<=used;footer_crc<=checksum;footer_generation<=frame_generation;
   footer_final<=last_packet;footer_busy<=1;footer_at<=0;used<=0;block_crc<=16'hffff;end
 endtask
 always @(posedge src_clk or posedge src_reset)begin
  if(src_reset)begin
   hfault_sync<=0;host_up_sync<=0;rgray_s1<=0;rgray_s2<=0;sfault<=0;wbin<=0;wgray<=0;
   used<=0;record_open319<=0;crc_pending<=0;crc_byte<=0;block_crc<=16'hffff;flush_record<=0;
   footer_length<=0;footer_crc<=0;footer_generation<=0;footer_final<=0;footer_busy<=0;footer_at<=0;
  end else begin
   hfault_sync<={hfault_sync[0],hfault};host_up_sync<={host_up_sync[0],hr[1]};
   rgray_s1<=rgray;rgray_s2<=rgray_s1;
   if(abort_source)sfault<=1;
   if(source_live)begin
    if(footer_busy)begin
     if(footer_at==5)begin footer_busy<=0;wbin<=wbin+1'b1;wgray<=gray(wbin+1'b1);end
     else footer_at<=footer_at+1'b1;
    end else begin
     if(record_valid&&!record_open319&&!full&&!crc_pending)begin
      if(!record_length||record_length>243)sfault<=1;
      else if(!room)begin if(!used)sfault<=1;else seal(block_crc,1'b0);end
      else begin record_open319<=1;flush_record<=record_flush;end
     end
     if(byte_valid&&byte_ready)begin
      if(record_last319)record_open319<=0;
      used<=used+1'b1;crc_pending<=1;crc_byte<=byte_data;
     end
     if(crc_pending)begin
      crc_pending<=0;block_crc<=crc_result;
      if(!record_open319&&(flush_record||used==248))seal(crc_result,flush_record);
     end
    end
   end
  end
 end
 reg read_seen,reading,request_ok280;
 reg [15:0] token;
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
 reg [7:0] read_byte,length;reg [15:0] checksum,head_generation;
 reg head_final,meta_valid,loading,check_generation;reg [3:0] load_step;
 reg snapshot_ready;
 wire [7:0] snapshot_length=snapshot_ready?length:8'd0;
 wire [15:0] snapshot_crc=checksum,snapshot_token=token;
 wire [7:0] read_address=loading?8'd250+{5'd0,load_step[3:1]}:count270[7:0]-8'd13;
 always @(posedge host_clk)read_byte<=memory[{rbin[1:0],read_address}];
 reg [7:0] reply;
 wire [7:0] response_flags={5'b10101,host_fault,ack_available,snapshot_ready};
 always @*begin
  reply=0;
  case(count270)
   8:reply=response_flags;9:reply=snapshot_length;
   10:reply=snapshot_token[15:8];11:reply=snapshot_token[7:0];12:reply=status_reply270;
   default:if(reading)begin
    if(count270>=13&&count270<13+snapshot_length)reply=read_byte;
    else if(count270==13+snapshot_length)reply=snapshot_crc[15:8];
    else if(count270==14+snapshot_length)reply=snapshot_crc[7:0];
   end
  endcase
 end
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin
   sfault_sync<=0;wgray_h1<=0;wgray_h2<=0;hfault<=0;rbin<=0;rgray<=0;
   read_seen<=0;reading<=0;token<=0;ack_pending<=0;ack_data<=0;miso_hold<=0;request_ok280<=0;
   snapshot_ready<=0;length<=0;checksum<=0;head_generation<=0;head_final<=0;
   meta_valid<=0;loading<=0;load_step<=0;check_generation<=0;
  end else begin
   sfault_sync<={sfault_sync[0],sfault};wgray_h1<=wgray;wgray_h2<=wgray_h1;
   if(abort_source)hfault<=1;
   if(ack_pending&&ack_send_ready)ack_pending<=0;
   if(!empty&&!meta_valid&&!loading)begin loading<=1;load_step<=0;end
   if(loading)begin
    load_step<=load_step+1'b1;
    if(load_step[0])case(load_step[3:1])
     0:length<=read_byte;1:head_final<=read_byte[0];
     2:head_generation[7:0]<=read_byte;3:head_generation[15:8]<=read_byte;
     4:checksum[15:8]<=read_byte;
     5:begin checksum[7:0]<=read_byte;loading<=0;meta_valid<=1;
      if(!length||length>248||(check_generation&&head_generation!=request_generation))hfault<=1;
      check_generation<=0;
     end
    endcase
   end
   if(!ss[1]&&!sck[1]&&prev_sck)miso_hold<=reply[7-bits270];
   if(ss[1])begin
    miso_hold<=0;
    if(!prev_ss&&ours)begin
     if(!request_ok280||bits270!=0||count270!=(command==8'hd5 ? 10'd8:reading?15+snapshot_length:13))begin
      hfault<=1;read_seen<=0;
     end else if(command==8'hd4)read_seen<=reading;
    end
   end else if(sck[1]&&!prev_sck&&bits270==7)begin
    if(count270==0)begin request_ok280<=0;reading<=0;end
    if(ours&&count270==7)begin
     if(host_fault||!request_crc_good||incoming!=8'ha5||
      (command==8'hd4 ? request_flags>1:request_flags!=3)||
      (request_flags[0]&&(!meta_valid||empty||!read_seen||request_token!=token||request_generation!=head_generation||token==16'hffff))||
      (!request_flags[0]&&(read_seen||request_token!=token||(!empty&&meta_valid&&head_generation!=request_generation)))||
      (command==8'hd5&&(!ack_available||!head_final||gray(rbin+1'b1)!=wgray_h2)))hfault<=1;
     else begin
      request_ok280<=1;read_seen<=0;
      if(request_flags[0])begin
       rbin<=rbin+1'b1;rgray<=gray(rbin+1'b1);token<=token+1'b1;meta_valid<=0;
       loading<=0;check_generation<=command==8'hd4;
      end
      if(command==8'hd5)begin ack_pending<=1;ack_data<={1'b1,request_generation};end
      else if(request_flags[0])begin
       snapshot_ready<=gray(rbin+1'b1)!=wgray_h2;reading<=gray(rbin+1'b1)!=wgray_h2;
      end else begin snapshot_ready<=!empty&&meta_valid;reading<=!empty&&meta_valid;end
     end
    end
   end
  end
 end
 assign crc_take270=count270<6&&(count270==0?(incoming==8'hd4||incoming==8'hd5):ours);
 assign status270={183'd0,(command==8'hd4&&count270>=8&&count270<=11),reply,7'd0,(hr[1]&&(host_fault||(!empty&&meta_valid)))};
endmodule
