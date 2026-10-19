// SPDX-License-Identifier: MIT
// R1 one map range. Host queue owns packet; aperture owns DMA bytes;
// NES core owns receipt; final display ACK is a different mailbox event.
module nes_range257(
 input wire nes_clk,host_clk,reset,cancel,
 input wire identity_valid,output wire identity_ready,
 input wire [31:0] serial,input wire [15:0] generation,input wire bank,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire miso,
 input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire bus_valid,
 output wire range_valid,input wire range_ready,output wire [11:0] range_first,range_count,
 output wire range_dma_done,input wire sealed,input wire core_idle,
 output wire display_ack,output wire retired,
 output wire staged,receipt_committed,output wire fault
);
 wire rst=reset||cancel;
 wire iv;wire [48:0] idata;
 reg have_identity;reg [48:0] identity;
 nes_native_mailbox206 #(.WIDTH(49)) admission(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
 .src_valid(identity_valid),.src_ready(identity_ready),.src_data({bank,generation,serial}),
 .dst_valid(iv),.dst_ready(!have_identity),.dst_data(idata));
 wire qr;wire [8:0] qlen;wire [7:0] qdata;reg [7:0] qaddr;
 reg qretire;wire qfault,selected;
 nes_queue257 queue(.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .selected(selected),.miso(miso),.sn_address(qaddr),.sn_data(qdata),.packet_ready(qr),.packet_length(qlen),
 .ack_write(1'b0),.ack_index(4'd0),.ack_byte(8'd0),.ack_publish(1'b0),.parser_retire(qretire),.fault(qfault));
 localparam IDLE=0,HREAD=1,HCAP=2,CHECK=3,OPEN=4,PREAD=5,PCAP=6,PUT=7,SEAL=8,RETIRE=9,DMA=10,SEND=11,WAIT_RECEIPT=12,CONSUME=13,DISPLAY=14,DONE=15;
 reg [3:0] state;reg failed;
 reg [7:0] header[0:19];reg [7:0] at,held;
 reg [11:0] length,first,count;reg [31:0] token;
 wire ready,put_ready,chunk_ready,pe,ce;wire [11:0] chunk_length;wire [31:0] chunk_token;
 wire [7:0] aperture_data;wire aoe,adir;
 nes_bulk_aperture188 aperture(.clk(host_clk),.reset(rst),.active(!failed&&!qfault),.stop(1'b0),
 .begin_valid(state==OPEN),.begin_length(length),.begin_token(token),.begin_ready(ready),
 .byte_valid(state==PUT),.byte_data(held),.byte_ready(put_ready),.seal(state==SEAL),.cancel(1'b0),.producer_error(pe),
 .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),
 .consume(state==CONSUME),.consume_token(token),.consume_error(ce),
 .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe),.dir(adir));
 assign staged=chunk_ready;assign receipt_committed=state==DISPLAY||state==DONE;
 wire mv,mready;wire [23:0] md;reg [1:0] ns;
 nes_native_mailbox206 #(.WIDTH(24)) consumed(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid(state==SEND),.src_ready(mready),.src_data({first,count}),.dst_valid(mv),.dst_ready(ns==3),.dst_data(md));
 assign range_first=md[23:12];assign range_count=md[11:0];
 assign range_valid=mv&&ns==0&&!rst;assign range_dma_done=ns==1&&!rst;
 wire back_ready,bv;wire [0:0] unused;
 nes_native_mailbox206 #(.WIDTH(1)) receipt(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
 .src_valid(ns==3),.src_ready(back_ready),.src_data(1'b1),.dst_valid(bv),.dst_ready(state==WAIT_RECEIPT),.dst_data(unused));
 always @(posedge nes_clk or posedge rst)begin
  if(rst)ns<=0;
  else case(ns)
   0:if(mv&&range_ready)ns<=1;
   1:ns<=2;
   2:if(range_ready)ns<=3;
   3:if(back_ready)ns<=0;
  endcase
 end
 (* async_reg="true" *) reg [1:0] sealed_sync;
 wire fv,fr;wire [0:0] final_data;reg final_send;
 nes_native_mailbox206 #(.WIDTH(1)) final_ack(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid(final_send),.src_ready(fr),.src_data(1'b1),.dst_valid(fv),.dst_ready(sealed),.dst_data(final_data));
 assign display_ack=fv&&sealed&&!rst;
 reg final_seen;assign retired=final_seen&&core_idle&&!rst;
 always @(posedge nes_clk or posedge rst)begin
  if(rst)final_seen<=0;else if(display_ack)final_seen<=1;
 end
 // Raw SNES writes are sampled and accepted once at their completed edge.
 (* async_reg="true" *) reg [23:0] am,asyn;
 (* async_reg="true" *) reg [7:0] dm,ds;
 (* async_reg="true" *) reg wm,ws,rm,rs;
 reg wp,rp;reg [23:0] ap;reg [7:0] dp;
 reg [11:0] read_count;
 reg [31:0] written;reg [3:0] mask;
 reg [7:0] control;
 always @*begin
  control=0;
  case(address[7:0])
   8'h40:control=state==DMA&&chunk_ready;
   8'h41:control={7'd0,identity[48]};
   8'h42:control=length[7:0];8'h43:control={4'd0,length[11:8]};
   8'h44:control=first[7:0];8'h45:control={4'd0,first[11:8]};
   8'h46:control=identity[39:32];8'h47:control=identity[47:40];
   8'h48:control=token[7:0];8'h49:control=token[15:8];8'h4a:control=token[23:16];8'h4b:control=token[31:24];
   8'h51:control=receipt_committed;8'h52:control=sealed_sync[1];
   default:control=0;
  endcase
 end
 assign data_out=address[23:8]==16'h0060 ? control : aperture_data;
 assign bus_valid=!rst&&!fault&&((address[23:8]==16'h0060&&!read_n&&write_n)||!aoe);
 assign fault=failed||qfault||pe||ce;
 integer j;
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin
   state<=IDLE;failed<=0;have_identity<=0;identity<=0;qaddr<=0;at<=0;held<=0;qretire<=0;
   length<=0;first<=0;count<=0;token<=0;am<=0;asyn<=0;ap<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;
   mask<=0;written<=0;sealed_sync<=0;final_send<=0;rm<=1;rs<=1;rp<=1;read_count<=0;
   for(j=0;j<20;j=j+1)header[j]<=0;
  end else begin
   am<=address;asyn<=am;ap<=asyn;dm<=data_in;ds<=dm;dp<=ds;wm<=write_n;ws<=wm;wp<=ws;
   rm<=read_n;rs<=rm;rp<=rs;
   sealed_sync<={sealed_sync[0],sealed};qretire<=0;
   if(final_send&&fr)final_send<=0;
   if(iv&&!have_identity)begin identity<=idata;have_identity<=1;end
   if(pe||ce||qfault)failed<=1;
   if(!failed&&!qfault)begin
    if(rs&&!rp&&ap[23:11]==13'h801)begin
     if(state!=DMA||!chunk_ready||read_count>=length||ap!=24'h400800+read_count)failed<=1;
     else read_count<=read_count+1'b1;
    end
    if(ws&&!wp)begin
     if(ap>=24'h00604c&&ap<=24'h00604f)begin written[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;end
     if(ap==24'h006050)begin
      mask<=0;
      if(state!=DMA||!chunk_ready||read_count!=length||dp!=8'ha5||mask!=15||written!=token)failed<=1;
      else state<=SEND;
     end
     if(ap==24'h006058)begin
      mask<=0;
      if(state!=DISPLAY||!sealed_sync[1]||dp!=8'h5a||mask!=15||written!=token)failed<=1;
      else begin final_send<=1;state<=DONE;end
     end
    end
    case(state)
     IDLE:if(qr&&have_identity)begin qaddr<=0;at<=0;state<=HREAD;end
     HREAD:state<=HCAP;
     HCAP:begin header[at]<=qdata;if(at==19)state<=CHECK;else begin at<=at+1'b1;qaddr<=qaddr+1'b1;state<=HREAD;end end
     CHECK:begin
      if(header[0]!=9||header[1]!={7'd0,identity[48]}||{header[3],header[2]}!=0||
       {header[7],header[6],header[5],header[4]}!=identity[31:0]||{header[9],header[8]}!=identity[47:32]||
       header[11]>7||header[15]!=0||header[14]==0||header[14]>64||header[14][0]||
       {header[13],header[12]}!=header[14]+16'd4||qlen!=header[14]+9'd20||
       {header[11],header[10]}+({8'd0,header[14]}>>1)>2048||{header[19],header[18],header[17],header[16]}==0)failed<=1;
      else begin first<={header[11][3:0],header[10]};length<={4'd0,header[14]};count<=header[14]>>1;
       token<={header[19],header[18],header[17],header[16]};state<=OPEN;end
     end
     OPEN:if(ready)begin at<=0;qaddr<=20;state<=PREAD;end
     PREAD:state<=PCAP;
     PCAP:begin held<=qdata;state<=PUT;end
     PUT:if(put_ready)begin if(at+1==length)state<=SEAL;else begin at<=at+1'b1;qaddr<=qaddr+1'b1;state<=PREAD;end end
     SEAL:state<=RETIRE;
     RETIRE:begin qretire<=1;state<=DMA;end
     SEND:if(mready)state<=WAIT_RECEIPT;
     WAIT_RECEIPT:if(bv)state<=CONSUME;
     CONSUME:state<=DISPLAY;
     default:;
    endcase
   end
  end
 end
endmodule
