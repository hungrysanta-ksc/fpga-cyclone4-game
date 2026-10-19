// SPDX-License-Identifier: MIT
// Bounded integration. SHARED=0 is the identical serialized schedule with
// separate tile/map apertures, for a like-for-like RAM/control comparison.
module nes_mux258 #(parameter SHARED=1,parameter [31:0] INITIAL_TOKEN=1)(
 input wire nes_clk,host_clk,reset,cancel,
 input wire identity_valid,output wire identity_ready,
 input wire [31:0] serial,input wire [15:0] generation,input wire bank,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire miso,
 input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire bus_valid,
 input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data,
 input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind,
 input wire [9:0] tile_slot,input wire [15:0] tile_generation,
 input wire end_valid,output wire end_ready,input wire [15:0] end_generation,
 output wire range_valid,input wire range_ready,output wire [11:0] range_first,range_count,
 output wire range_dma_done,input wire sealed,core_idle,
 output wire display_ack,retired,staged,receipt_committed,fault,
 output wire ordinary_ready,output wire [31:0] next_token
);
 wire rst=reset||cancel;
 localparam IDLE=0,HREAD=1,HCAP=2,CHECK=3,OPEN=4,PREAD=5,PCAP=6,PUT=7,SEAL=8,RETIRE=9,DMA=10,SEND=11,WAIT_RECEIPT=12,CONSUME=13,NORMAL=14,ACKWAIT=15,DONE=16;
 localparam NONE=0,TILE=1,MAP=2;
 reg [4:0] state;reg [1:0] owner;reg failed,have_identity,tile_ended;
 reg [48:0] identity;wire iv,admission_ready;wire [48:0] idata;reg nes_admitted;
 wire can_admit=!have_identity||state==DONE;
 nes_native_mailbox206 #(.WIDTH(49)) admission(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
 .src_valid(identity_valid&&!nes_admitted),.src_ready(admission_ready),.src_data({bank,generation,serial}),
 .dst_valid(iv),.dst_ready(can_admit),.dst_data(idata));
 assign identity_ready=admission_ready&&!nes_admitted&&!rst;
 always @(posedge nes_clk or posedge rst)begin
  if(rst)nes_admitted<=0;
  else if(identity_valid&&identity_ready)nes_admitted<=1;
  else if(display_ack)nes_admitted<=0;
 end
 // STOP burns allocated tokens and admitted serials. Only board reset starts
 // a new namespace; a caller must quiesce the physical bus across that reset.
 reg [31:0] allocation,last_serial;
 wire allocate;assign next_token=allocation;
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin allocation<=INITIAL_TOKEN;last_serial<=0;end
  else begin
   if(!rst&&allocate&&allocation!=32'hffffffff)allocation<=allocation+1'b1;
   if(!rst&&iv&&can_admit&&idata[31:0]>last_serial)last_serial<=idata[31:0];
  end
 end
 reg [7:0] header[0:19];reg [7:0] at,held,parser_address;
 reg [11:0] length,first,count;reg [31:0] token;reg [15:0] packet_seq;
 reg qretire;wire qr,qfault,qdone;wire [8:0] qlen;wire [7:0] qdata;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg wm,ws,rm,rs;
 reg wp,rp;reg [23:0] ap,qtag;reg [7:0] dp;
 wire write_end=ws&&!wp&&rp;
 wire ack_write=write_end&&ap>=24'h006010&&ap<=24'h00601b&&state==NORMAL;
 wire ack_publish=write_end&&ap==24'h00601c&&dp==8'ha5&&state==NORMAL;
 wire [7:0] qaddr=state==NORMAL?asyn[7:0]:parser_address;
 nes_queue258 queue(.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .selected(),.miso(miso),.sn_address(qaddr),.sn_data(qdata),.packet_ready(qr),.packet_length(qlen),
 .ack_write(ack_write),.ack_index(ap[3:0]),.ack_byte(dp),.ack_publish(ack_publish),.parser_retire(qretire),.ack_done(qdone),.fault(qfault));
 assign ordinary_ready=state==NORMAL&&qr&&!fault&&!rst;
 wire tbeg,tput,tseal,trequest,tfault,tend,tkind;wire [7:0] tdata;
 wire [9:0] tslot;wire [15:0] tgen;
 wire begin_ready,put_ready,chunk_ready,pe,ce;
 wire [11:0] chunk_length;wire [31:0] chunk_token;
 wire tile_consume,map_consume;wire consume=tile_consume||map_consume;
 nes_tile_producer258 tiles(.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.active(1'b1),.stop(1'b0),.source_fault(failed||qfault),
 .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
 .end_valid(end_valid),.end_ready(end_ready),.end_generation(end_generation),.token_seed(allocation),
 .request_stage(trequest),.grant_stage(owner==TILE),.p_begin(tbeg),.p_put(tput),.p_seal(tseal),.p_data(tdata),
 .begin_ready(begin_ready&&owner==TILE),.put_ready(put_ready&&owner==TILE),.producer_error(pe&&owner==TILE),
 .chunk_ready(chunk_ready&&owner==TILE),.chunk_length(chunk_length),.chunk_token(chunk_token),
 .chunk_kind(tkind),.chunk_slot(tslot),.chunk_generation(tgen),.consume(tile_consume),.consume_token(chunk_token),
 .fault(tfault),.end_sealed(tend),.sealed_generation());
 wire mbeg=state==OPEN&&owner==MAP&&!failed&&token==allocation&&allocation!=32'hffffffff;
 wire mput=state==PUT&&owner==MAP;
 wire mseal=state==SEAL&&owner==MAP;
 wire [7:0] aperture_data;wire aoe;
 assign allocate=begin_ready&&((owner==TILE&&tbeg)||(owner==MAP&&mbeg));
 genvar k;
 generate if(SHARED)begin:shared_ram
  nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(host_clk),.reset(rst),.active(!fault),.stop(1'b0),
   .begin_valid(owner==TILE?tbeg:mbeg),.begin_length(owner==TILE?12'd2048:length),.begin_token(allocation),.begin_ready(begin_ready),
   .byte_valid(owner==TILE?tput:mput),.byte_data(owner==TILE?tdata:held),.byte_ready(put_ready),.seal(owner==TILE?tseal:mseal),.cancel(1'b0),.producer_error(pe),
   .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),.consume(consume),.consume_token(chunk_token),.consume_error(ce),
   .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe),.dir());
 end else begin:separate_ram
  wire [1:0] br,pr,cr,pes,ces,oe;wire [11:0] len[0:1];wire [31:0] tok[0:1];wire [7:0] dat[0:1];
  for(k=0;k<2;k=k+1)begin:lane
   nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(host_clk),.reset(rst),.active(!fault),.stop(1'b0),
    .begin_valid(k==0?tbeg:mbeg),.begin_length(k==0?12'd2048:length),.begin_token(allocation),.begin_ready(br[k]),
    .byte_valid(k==0?tput:mput),.byte_data(k==0?tdata:held),.byte_ready(pr[k]),.seal(k==0?tseal:mseal),.cancel(1'b0),.producer_error(pes[k]),
    .chunk_ready(cr[k]),.chunk_length(len[k]),.chunk_token(tok[k]),.consume(k==0?tile_consume:map_consume),.consume_token(tok[k]),.consume_error(ces[k]),
    .address(address),.read_n(read_n||owner!=(k+1)),.write_n(write_n),.data_out(dat[k]),.oe_n(oe[k]),.dir());
  end
  assign begin_ready=owner==TILE?br[0]:br[1];assign put_ready=owner==TILE?pr[0]:pr[1];
  assign chunk_ready=owner==TILE?cr[0]:owner==MAP?cr[1]:1'b0;
  assign chunk_length=owner==TILE?len[0]:len[1];assign chunk_token=owner==TILE?tok[0]:tok[1];
  assign aperture_data=owner==TILE?dat[0]:dat[1];assign aoe=owner==TILE?oe[0]:oe[1];assign pe=|pes;assign ce=|ces;
 end endgenerate
 wire mv,mready;wire [23:0] md;reg [1:0] ns;
 nes_native_mailbox206 #(.WIDTH(24)) consumed(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid(state==SEND),.src_ready(mready),.src_data({first,count}),.dst_valid(mv),.dst_ready(ns==3),.dst_data(md));
 assign range_first=md[23:12];assign range_count=md[11:0];assign range_valid=mv&&ns==0&&!rst;assign range_dma_done=ns==1&&!rst;
 wire back_ready,bv;
 nes_native_mailbox206 #(.WIDTH(1)) receipt(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
 .src_valid(ns==3),.src_ready(back_ready),.src_data(1'b1),.dst_valid(bv),.dst_ready(state==WAIT_RECEIPT),.dst_data());
 always @(posedge nes_clk or posedge rst)begin
  if(rst)ns<=0;else case(ns)0:if(mv&&range_ready)ns<=1;1:ns<=2;2:if(range_ready)ns<=3;3:if(back_ready)ns<=0;endcase
 end
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] sealed_sync;
 wire fv,fr;reg final_send,final_seen;
 nes_native_mailbox206 #(.WIDTH(1)) final_ack(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid(final_send),.src_ready(fr),.src_data(1'b1),.dst_valid(fv),.dst_ready(sealed),.dst_data());
 assign display_ack=fv&&sealed&&!rst;assign retired=final_seen&&core_idle&&!rst;
 always @(posedge nes_clk or posedge rst)begin
  if(rst)final_seen<=0;else if(identity_valid&&identity_ready)final_seen<=0;else if(display_ack)final_seen<=1;
 end
 reg [31:0] written,last_map_token;reg [3:0] mask;reg [11:0] read_count;reg map_receipt;
 wire [31:0] visible_token=chunk_ready?chunk_token:last_map_token;
 wire consume_write=write_end&&ap==24'h006050;
 wire good_consume=chunk_ready&&read_count==chunk_length&&dp==8'ha5&&mask==15&&written==chunk_token;
 assign tile_consume=consume_write&&good_consume&&owner==TILE&&!rst&&!fault;
 assign map_consume=state==CONSUME&&!rst&&!fault;
 assign staged=chunk_ready&&!fault&&!rst;assign receipt_committed=map_receipt&&!fault&&!rst;
 assign fault=failed||qfault||tfault; // aperture error pulses are latched below
 reg [7:0] control;
 always @*begin
  control=0;
  case(address[7:0])
   8'h00:control=ordinary_ready;8'h01:control={fault,7'd0};8'h04:control=qlen[7:0];8'h05:control={7'd0,qlen[8]};
   8'h40:control=chunk_ready&&(owner==TILE||state==DMA);
   8'h41:control={5'd0,identity[48],owner==MAP,tkind&&owner==TILE};
   8'h42:control=chunk_length[7:0];8'h43:control={4'd0,chunk_length[11:8]};
   8'h44:control=owner==MAP?first[7:0]:tslot[7:0];8'h45:control=owner==MAP?{4'd0,first[11:8]}:{6'd0,tslot[9:8]};
   8'h46:control=identity[39:32];8'h47:control=identity[47:40];
   8'h48:control=visible_token[7:0];8'h49:control=visible_token[15:8];8'h4a:control=visible_token[23:16];8'h4b:control=visible_token[31:24];
   8'h51:control=receipt_committed;8'h52:control=sealed_sync[1];
   default:;
  endcase
 end
 assign data_out=address[23:8]==16'h0060 ? control : address[23:8]==16'h4000 ? qdata : aperture_data;
 assign bus_valid=!rst&&!fault&&!read_n&&write_n&&((address[23:8]==16'h0060)||
  (ordinary_ready&&address[23:8]==16'h4000&&{1'b0,address[7:0]}<qlen&&qtag==address)||!aoe);
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin
   state<=IDLE;owner<=NONE;failed<=0;have_identity<=0;identity<=0;tile_ended<=0;at<=0;held<=0;parser_address<=0;qretire<=0;packet_seq<=0;
   length<=0;first<=0;count<=0;token<=0;last_map_token<=0;map_receipt<=0;
   am<=0;asyn<=0;ap<=0;qtag<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;
   written<=0;mask<=0;read_count<=0;sealed_sync<=0;final_send<=0;
   // Header bytes are read completely before use; no payload/header reset.
  end else begin
   am<=address;asyn<=am;ap<=asyn;qtag<=asyn;dm<=data_in;ds<=dm;dp<=ds;wm<=write_n;ws<=wm;wp<=ws;rm<=read_n;rs<=rm;rp<=rs;
   sealed_sync<={sealed_sync[0],sealed};qretire<=0;if(final_send&&fr)final_send<=0;
   if(pe||ce||tfault||qfault)failed<=1;
   if(iv&&can_admit)begin
    if(idata[31:0]<=last_serial)failed<=1;
    else begin identity<=idata;have_identity<=1;packet_seq<=0;state<=IDLE;map_receipt<=0;last_map_token<=0;end
   end
   if(!failed&&!qfault&&!tfault)begin
    if(owner==NONE&&have_identity&&state!=DONE)begin
     if(state==OPEN)owner<=MAP;
     else if(trequest)begin owner<=TILE;tile_ended<=0;end
    end
    if(owner==TILE)begin
     if(tend)tile_ended<=1;
     if((tile_ended||tend)&&!chunk_ready)begin owner<=NONE;tile_ended<=0;end
     if(chunk_ready&&tgen!=identity[47:32])failed<=1;
    end
    if(consume)read_count<=0;
    if(rs&&!rp&&ap[23:11]==13'h801)begin
     if(!chunk_ready||read_count>=chunk_length||ap!=24'h400800+read_count)failed<=1;
     else read_count<=read_count+1'b1;
    end
    if(write_end)begin
     if(ap>=24'h006010&&ap<=24'h00601c&&state!=NORMAL)failed<=1;
     if(ap==24'h00601c)begin if(!ack_publish)failed<=1;else state<=ACKWAIT;end
     if(ap>=24'h00604c&&ap<=24'h00604f)begin written[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;end
     if(consume_write)begin
      mask<=0;if(!good_consume||(owner!=TILE&&state!=DMA))failed<=1;
      else if(owner==MAP)state<=SEND;
     end
     if(ap==24'h006058)begin
      mask<=0;
      if(state!=IDLE||owner!=NONE||qr||trequest||!map_receipt||!sealed_sync[1]||dp!=8'h5a||mask!=15||written!=last_map_token)failed<=1;
      else begin final_send<=1;state<=DONE;end
     end
    end
    case(state)
     IDLE:if(qr&&have_identity)begin parser_address<=0;at<=0;state<=HREAD;end
     HREAD:state<=HCAP;
     HCAP:begin header[at]<=qdata;if(at==19||(at==15&&header[0]!=9))state<=CHECK;else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=HREAD;end end
     CHECK:begin
      if(header[0]==0||header[0]>9||header[1]!={7'd0,identity[48]}||{header[3],header[2]}!=packet_seq||packet_seq==16'hffff||
       {header[7],header[6],header[5],header[4]}!=identity[31:0]||{header[9],header[8]}!=identity[47:32])failed<=1;
      else if(header[0]!=9)state<=NORMAL;
      else if(header[11]>7||header[15]!=0||header[14]==0||header[14]>64||header[14][0]||
       {header[13],header[12]}!=header[14]+16'd4||qlen!=header[14]+9'd20||
       {header[11],header[10]}+({8'd0,header[14]}>>1)>2048)failed<=1;
      else begin first<={header[11][3:0],header[10]};length<={4'd0,header[14]};count<=header[14]>>1;
       token<={header[19],header[18],header[17],header[16]};state<=OPEN;map_receipt<=0;end
     end
     OPEN:if(owner==MAP)begin
      if(token!=allocation||allocation==32'hffffffff)failed<=1;
      else if(begin_ready)begin at<=0;parser_address<=20;state<=PREAD;end
     end
     PREAD:state<=PCAP;PCAP:begin held<=qdata;state<=PUT;end
     PUT:if(put_ready)begin if(at+1==length)state<=SEAL;else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end end
     SEAL:state<=RETIRE;
     RETIRE:begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=DMA;end
     SEND:if(mready)state<=WAIT_RECEIPT;
     WAIT_RECEIPT:if(bv)state<=CONSUME;
     CONSUME:begin state<=IDLE;owner<=NONE;last_map_token<=token;map_receipt<=1;end
     ACKWAIT:if(qdone)begin packet_seq<=packet_seq+1'b1;state<=IDLE;end
     default:;
    endcase
   end
  end
 end
endmodule
