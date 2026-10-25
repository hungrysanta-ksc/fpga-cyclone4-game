// SPDX-License-Identifier: MIT
// Bounded integration. SHARED=0 is the identical serialized schedule with
// separate tile/map apertures, for a like-for-like RAM/control comparison.
module nes_output260 #(parameter SHARED=1,parameter [31:0] INITIAL_TOKEN=1)(output wire [33:0] read359,input wire ready359,private359,
output wire jobs_committed336,output wire [7:0] expected_data332,input wire [8:0] expected_addr332,output wire queue_admit319,output wire exec_start298,output wire [1:0] exec_kind298,
 output wire [3:0] exec_op298,output wire [8:0] exec_length298,
 output wire [7:0] exec_data298,input wire exec_busy298,exec_done298,
 input wire [7:0] exec_addr298,
output wire crc_reset287,
output wire grant278,
output wire [31:0] grant_epoch278,
output wire [31:0] grant_serial278,
output wire [15:0] grant_generation278,
output wire [2:0] grant_raw278,
output wire host_ack278,
input wire crc_done278,
input wire [3:0] crc_index278,
input wire init278,
 input wire [8:0] manifest_at282,input wire manifest_started282,
input wire [31:0] epoch278,input wire [2:0] raw278,
 input wire [113:0] link270,output wire [199:0] status270,output wire crc_take270,

 input wire nes_clk,host_clk,reset,cancel,
 input wire identity_valid,output wire identity_ready,
 input wire [31:0] serial,input wire [15:0] generation,input wire bank,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire miso,output wire selected,
 input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire bus_valid,
 input wire tile_valid,output wire tile_ready,input wire [7:0] tile_data,
 input wire [4:0] tile_index,input wire [5:0] tile_length,input wire [1:0] tile_kind,
 input wire [9:0] tile_slot,input wire [15:0] tile_generation,
 input wire end_valid,end_partial295,output wire end_ready,input wire [15:0] end_generation,
 output wire display_write,display_request,input wire display_request_ready,
 input wire display_response_valid,output wire display_response_ready,input wire [7:0] display_response,
 output wire range_valid,input wire range_ready,output wire [11:0] range_first,range_count,
 output wire range_dma_done,input wire sealed,core_idle,
 output wire display_ack,retired,staged,receipt_committed,fault,
output wire ordinary_range,output wire [11:0] ordinary_first,ordinary_end300,
 output wire ordinary_stream,output wire [7:0] ordinary_byte,input wire ordinary_stream_ready,
 output wire ordinary_check,ordinary_finish,ordinary_hash_start,ordinary_hash_byte,
 output wire [1:0] ordinary_hash_kind,output wire [3:0] ordinary_hash_index,input wire ordinary_hash_ready,
 output wire context_valid,output wire [7:0] context_data,input wire context_ready,
 output wire begin_valid,output wire begin_bank,output wire [2:0] begin_raw,
 output wire tile_closed267,
 output wire ordinary_ready,output wire [31:0] next_token
);
 wire rst=reset||cancel;
 reg invalidate_banks;
 wire status_address=address==24'h006001;
 localparam IDLE=0,CHECK=3,OPEN=4,PREAD=5,PCAP=6,PUT=7,SEAL=8,RETIRE=9,DMA=10,SEND=11,WAIT_RECEIPT=12,CONSUME=13,NORMAL=14,ACKWAIT=15,DONE=16,DREAD=17,DCAP=18,DCHECK=19,BRET=20,PREWAIT=21,BSTART=22,BWAIT=23,OSETUP=24,OTILE=25,OSELECT=26,ODATA=27,OREAD=PREAD,OCAP=PCAP,ORLE=30,OCHECKNEXT=31,OISSUE=32,OWAIT=33,OCERT=34,OFINISH=35,ORET=36,DREQ=37,DWAIT=38,DPRESENT=39,OTREAD=PREAD;
 localparam XBEGIN298=40,XWAIT298=41;
 localparam MREAD313=42,MCAP313=43,MNEXT313=44,MISSUE313=45,
  MWAIT313=46,MDONE313=47,MSEALWAIT313=53;
 reg [7:0] run_left313;reg run_zero313;
 reg [8:0] manifest_byte313;
 reg display_byte313,requirements_complete313;
 reg [8:0] map_received313;

 localparam TILEWAIT313=54,HLOAD315=55,HCHECK315=56;
 localparam NONE=0,TILE=1,MAP=2;
 reg [5:0] state;reg [1:0] owner;reg failed,have_identity;wire range_idle295;
 reg [83:0] admitted286;wire [48:0] identity=admitted286[48:0];wire iv,admission_ready;wire [83:0] full_idata278;wire [48:0] idata=full_idata278[48:0];reg nes_admitted;
 wire can_admit=init278&&(!have_identity||state==DONE);
 assign grant278=iv&&can_admit&&!rst;
 assign grant_epoch278=admitted286[83:52];assign grant_raw278=admitted286[51:49];
 assign grant_generation278=identity[47:32];assign grant_serial278=identity[31:0];

 nes_native_mailbox206 #(.WIDTH(84)) admission(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
 .src_valid(identity_valid&&!nes_admitted),.src_ready(admission_ready),.src_data({epoch278,raw278,bank,generation,serial}),
 .dst_valid(iv),.dst_ready(can_admit),.dst_data(full_idata278));
 assign identity_ready=admission_ready&&!nes_admitted&&!rst;
 always @(posedge nes_clk or posedge rst)begin
  if(rst)nes_admitted<=0;
  else if(identity_valid&&identity_ready)nes_admitted<=1;
  else if(display_ack)nes_admitted<=0;
 end
 // STOP burns allocated tokens and admitted serials. Only board reset starts
 // a new namespace; a caller must quiesce the physical bus across that reset.
 reg [31:0] allocation,last_serial,ordinary_next313;
 wire allocate,ordinary_allocate313;assign next_token=allocation;
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin allocation<=INITIAL_TOKEN;last_serial<=0;ordinary_next313<=1;end
  else begin
   if(!rst&&ordinary_allocate313&&ordinary_next313!=32'hffffffff)
    ordinary_next313<=ordinary_next313+1'b1;
   if(!rst&&allocate&&allocation!=32'hffffffff)allocation<=allocation+1'b1;
   if(!rst&&iv&&can_admit&&idata[31:0]>last_serial)last_serial<=idata[31:0];
  end
 end
 reg prelude_mode,prelude_done,begun;wire [2:0] prelude_raw=admitted286[51:49];
 reg batch;reg [8:0] cursor;
 typedef struct packed {
  logic [7:0] op,section;logic [15:0] start,encoded,span;
  logic [31:0] token;logic [7:0] left;logic [16:0] endpos;
 } active_t305;
 active_t305 active305;
 wire [7:0] remaining=active305.left;
 wire [7:0] header[0:20];
 assign header[0]=active305.op;assign header[1]=active305.section;
 assign header[10]=active305.start[7:0];assign header[11]=active305.start[15:8];
 assign header[12]=active305.encoded[7:0];assign header[13]=active305.encoded[15:8];
 assign header[14]=active305.span[7:0];assign header[15]=active305.span[15:8];
 assign header[16]=active305.token[7:0];assign header[17]=active305.token[15:8];
 assign header[18]=active305.token[23:16];assign header[19]=active305.token[31:24];
 assign header[20]=active305.left;
 reg [7:0] at,held;reg [8:0] parser_address;
 wire [11:0] length=(active305.op==2||active305.op==4||active305.op==5||active305.op==8)?active305.encoded[11:0]:active305.span[11:0],first=active305.start[12:1],count={1'b0,active305.span[11:1]};wire [31:0] token=active305.token;reg [15:0] packet_seq;
 reg tiles_closed;assign tile_closed267=tiles_closed;
 wire data_command278;
 wire consume_record312=!rst&&!fault&&state==CONSUME&&(!batch||remaining==1);
 reg qretire;wire qr,qfault,qdone;wire [8:0] queue_length312;reg [8:0] qlen;wire [7:0] qdata;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg wm,ws,rm,rs;
 reg wp,rp;reg [23:0] ap,qtag;reg [7:0] dp;
 wire write_end=ws&&!wp&&rp;
 assign qdone=1'b0;
 wire display_address=address>=24'h006070&&address<24'h00607c;
 wire display_read=ap>=24'h006070&&ap<24'h00607c;
 wire requirements313=header[0]==15&&header[1]==1;
 wire rle313=header[0]==11||(requirements313&&parser_address>40);
 wire [9:0] run_end313={1'b0,manifest_byte313}+{3'd0,qdata[6:0]}+10'd1;
 wire metadata313=(state==MREAD313||state==MCAP313||state==MNEXT313||state==MISSUE313||state==MWAIT313||state==MDONE313||state==MSEALWAIT313);
 wire receipt_done313=state==XWAIT298&&range_ready;
 assign expected_data332=qdata;
 wire canonical_read313=header[0]==3&&metadata313;
 wire canonical_bad332=!display_byte313&&
  (header[0]==15?manifest_byte313>=9'd166:manifest_byte313[8]);
 wire canonical_write313=header[0]!=3&&state==MISSUE313&&!rst&&!fault&&!canonical_bad332;
 wire [8:0] canonical_address313=canonical_read313?expected_addr332:
  display_byte313?{4'b1110,(parser_address[4:0]-5'd17)}:
  {header[0]==15,manifest_byte313[7:0]};

 wire [7:0] qaddr=parser_address[7:0];
 wire [127:0] progress_status;
 wire [191:0] record312={72'd0,active305.left,active305.token,active305.encoded,active305.span,active305.start,packet_seq,active305.section,active305.op};
 wire record_valid312,storage_empty312;wire [4:0] record_at312;wire [7:0] record_byte312;
 nes_queue260 queue(.admit319(queue_admit319),.expected_select313(canonical_read313||canonical_write313),
 .expected_write313(canonical_write313),.expected_address313(canonical_address313),.expected_data313(held),.frame_start312(grant278),.frame_serial312(identity[31:0]),
 .frame_generation312(identity[47:32]),.record312(record312),.load_enable312(state==HLOAD315),.load_at315(at[3:0]),
 .storage_empty312(storage_empty312),.record_valid312(record_valid312),.record_at312(record_at312),.record_byte312(record_byte312),.link270(link270),.status270(status270),.crc_take270(crc_take270),.progress_status(progress_status),.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .selected(selected),.miso(miso),.sn_address(qaddr),.sn_data(qdata),.packet_ready(qr),.packet_length(queue_length312),
 .parser_retire(qretire),.consume_record312(consume_record312),.fault(qfault));
 
 wire tbeg,tput,tseal,trequest,tfault,tend,tkind;wire [7:0] tdata;
 wire [9:0] tslot;wire [15:0] tgen;
 wire begin_ready,put_ready,chunk_ready,pe,ce;
 wire [11:0] chunk_length;wire [31:0] chunk_token;
 assign ordinary_ready=(state==DMA&&data_command278&&chunk_ready)&&!fault&&!rst&&!invalidate_banks;
 wire [31:0] identity_token331=chunk_ready?chunk_token:allocation;
 assign progress_status={
  5'd0,owner==MAP,chunk_ready,tiles_closed,
  identity_token331[7:0],identity_token331[15:8],identity_token331[23:16],identity_token331[31:24],32'd0,
  chunk_length[7:0],4'd0,chunk_length[11:8],5'd0,identity[48],owner==MAP,tkind&&owner==TILE,
  tslot[7:0],6'd0,tslot[9:8],identity[39:32],identity[47:40]};
 wire tile_consume,map_consume;wire consume=tile_consume||map_consume;
 nes_tile_producer260 tiles(.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.active(1'b1),.stop(1'b0),.source_fault(failed||qfault),
 .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
 .end_valid(end_valid),.end_partial295(end_partial295),.end_ready(end_ready),.end_generation(end_generation),.token_seed(allocation),
 .request_stage(trequest),.grant_stage(owner==TILE),.p_begin(tbeg),.p_put(tput),.p_seal(tseal),.p_data(tdata),
 .begin_ready(begin_ready&&owner==TILE),.put_ready(put_ready&&owner==TILE),.producer_error(pe&&owner==TILE),
 .chunk_ready(chunk_ready&&owner==TILE),.chunk_length(chunk_length),.chunk_token(chunk_token),
 .chunk_kind(tkind),.chunk_slot(tslot),.chunk_generation(tgen),.consume(tile_consume),.consume_token(chunk_token),
 .fault(tfault),.range_idle295(range_idle295),.end_sealed(tend),.sealed_generation());
 wire mbeg=state==OPEN&&owner==MAP&&!failed&&(data_command278||(token==allocation&&allocation!=32'hffffffff));
 wire [15:0] startpos={header[11],header[10]};
 wire [15:0] outlen=header[0]==2?{header[13],header[12]}:{header[15],header[14]};
 localparam EXPAND325=57;
 reg [31:0] seed325;reg [11:0] expanded325;reg zero325;
 wire repeat325=data_command278&&header[0]!=2;
 wire [11:0] output325=zero325?12'd2:outlen[11:0];
 wire [1:0] lane325=expanded325[1:0]&(header[0]==8?2'd3:2'd1);
 wire mput=(state==PUT||state==EXPAND325)&&owner==MAP&&!prelude_mode;
 wire [7:0] payload325=state==EXPAND325?seed325[lane325*8+:8]:held;
 wire [15:0] destination325=(header[1]==3?16'h6000:header[1]==4?16'h6200:16'h6500)+{identity[48],15'd0}+startpos;
 wire [15:0] ppu325=startpos>>1;
 wire mseal=state==SEAL&&owner==MAP;
 wire [7:0] aperture_data;wire aoe;
 assign ordinary_allocate313=state==OPEN&&data_command278&&owner==MAP&&begin_ready;
 assign allocate=begin_ready&&((owner==TILE&&tbeg)||(owner==MAP&&mbeg&&!data_command278));

 genvar k;

 generate if(SHARED)begin:shared_ram
  nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(host_clk),.reset(rst),.active(!fault),.stop(1'b0),
   .wide325(owner==MAP&&data_command278),.begin_valid(owner==TILE?tbeg:mbeg),.begin_length(owner==TILE?12'd2048:(data_command278?outlen[11:0]:length)),.begin_token(owner==MAP&&data_command278?token:allocation),.begin_ready(begin_ready),
   .byte_valid(owner==TILE?tput:mput),.byte_data(owner==TILE?tdata:payload325),.byte_ready(put_ready),.seal(owner==TILE?tseal:mseal),.cancel(1'b0),.producer_error(pe),
   .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),.consume(consume),.consume_token(chunk_token),.consume_error(ce),
   .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe),.dir());
 end else begin:separate_ram
  wire [1:0] br,pr,cr,pes,ces,oe;wire [11:0] len[0:1];wire [31:0] tok[0:1];wire [7:0] dat[0:1];
  for(k=0;k<2;k=k+1)begin:lane
   nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(host_clk),.reset(rst),.active(!fault),.stop(1'b0),
    .wide325(k==1&&data_command278),.begin_valid(k==0?tbeg:mbeg),.begin_length(k==0?12'd2048:(data_command278?outlen[11:0]:length)),.begin_token(owner==MAP&&data_command278?token:allocation),.begin_ready(br[k]),
    .byte_valid(k==0?tput:mput),.byte_data(k==0?tdata:payload325),.byte_ready(pr[k]),.seal(k==0?tseal:mseal),.cancel(1'b0),.producer_error(pes[k]),
    .chunk_ready(cr[k]),.chunk_length(len[k]),.chunk_token(tok[k]),.consume(k==0?tile_consume:map_consume),.consume_token(tok[k]),.consume_error(ces[k]),
    .address(address),.read_n(read_n||owner!=(k+1)),.write_n(write_n),.data_out(dat[k]),.oe_n(oe[k]),.dir());
  end
  assign begin_ready=owner==TILE?br[0]:br[1];assign put_ready=owner==TILE?pr[0]:pr[1];
  assign chunk_ready=owner==TILE?cr[0]:owner==MAP?cr[1]:1'b0;
  assign chunk_length=owner==TILE?len[0]:len[1];assign chunk_token=owner==TILE?tok[0]:tok[1];
  assign aperture_data=owner==TILE?dat[0]:dat[1];assign aoe=owner==TILE?oe[0]:oe[1];assign pe=|pes;assign ce=|ces;
 end endgenerate
wire mready;


 reg [10:0] scroll_length;reg [8:0] ordinary_reads;
 wire [8:0] manifest_at=map_received313;
 wire [1:0] manifest_phase=!begun?2'd0:sealed?2'd2:requirements_complete313?2'd1:2'd0;
 reg tile_proven;
 wire [15:0] plen={header[13],header[12]};
 wire [31:0] previous_serial313=identity[31:0]-1'b1;
 wire [16:0] decode_end305={1'b0,startpos}+{1'b0,outlen};
 wire [16:0] descriptor_end287=active305.endpos;
 reg bad_data278;
 always @*begin
  bad_data278=0;
       if(sealed||!outlen||decode_end305>(header[1]==3?512:header[1]==4?544:header[1]==5?3418:0)||
          (header[0]==2?outlen!=plen:header[0]==8?(plen!=4||outlen[1:0]!=0):(plen!=2||outlen[0]!=0)))bad_data278=1;
       else if(header[1]==5&&((startpos<scroll_length&&(startpos!=0||decode_end305<scroll_length))||
        (decode_end305>3169&&((startpos>3169&&(startpos-16'd3169)%16!=0)||
          (decode_end305!=3418&&(decode_end305-16'd3169)%16!=0)))))bad_data278=1;

  if(header[1]==5&&decode_end305>1121&&
    ((startpos>1121&&startpos<3169&&(startpos-16'd1121)%16!=0)||
     (decode_end305<3169&&(decode_end305-17'd1121)%16!=0)))bad_data278=1;
  if(header[1]==3&&(startpos[3:0]!=0||outlen[3:0]!=0))bad_data278=1;
 end
 assign data_command278=header[0]==2||header[0]==4||header[0]==5||header[0]==8;

 wire bad_tile305=header[1]>1||plen!=4||!outlen||outlen>2048||
  (header[1]==0?(startpos[3:0]!=0||outlen[3:0]!=0||decode_end305>16384):
   (startpos[4:0]!=0||outlen[4:0]!=0||decode_end305>4096));
 wire bad_internal305=header[0]==15?(manifest_phase!=0||(header[1]==0?(qlen!=206||plen!=190):header[1]==1?(qlen<42||qlen>206):1'b1)||startpos!=0||outlen!=0):
  (header[0]==10||header[0]==11)?(manifest_phase!=1||header[1]!=2||startpos!=manifest_at||outlen!=0||plen==0):
  (manifest_phase!=1||manifest_at!=256||qlen!=16||plen!=0||startpos!=0||outlen!=0||header[1]!=0);
 // Capture only a tagged, valid SNES bus read, once per physical strobe.
 reg [11:0] read_count;
 reg tap_seen278,tap_fault278;
 wire [11:0] offset325=address-24'h400800;
 wire [15:0] tap_address278=startpos+{4'd0,offset325};
 wire tap_capture278=state==DMA&&chunk_ready&&!invalidate_banks&&!tap_seen278&&
  !read_n&&write_n&&bus_valid&&address>=24'h400800&&address<24'h401800;
 reg read_pending336;
 wire tap_idle278=ready359;
 wire [2:0] tap_state278=private359?3'd5:ready359?3'd0:3'd3;
 wire [7:0] tap_value278=aperture_data;
 wire tap_byte278=read359[33]&&read359[32];
 wire map336=header[0]==12||header[0]==14;
 wire [11:0] unit336=0;
 assign crc_reset287=state==CHECK;
 wire crc359=data_command278&&header[1]==5&&!zero325&&
  (tap_address278<scroll_length||(prelude_raw!=0&&tap_address278>=3169));
 wire start359=tap_address278==0||(tap_address278>=3169&&(tap_address278-3169)%16==0);
 assign read359={tap_capture278&&tap_idle278&&!read_pending336&&offset325==read_count&&read_count<chunk_length&&!rst&&!fault,
  crc359,start359,header[0][3:0],header[1][2:0],tap_address278,aperture_data};
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin tap_seen278<=0;tap_fault278<=0;read_pending336<=0;end
  else if(rst)begin tap_seen278<=0;read_pending336<=0;end
  else if(!fault)begin
   if(read_n)tap_seen278<=0;
   if(state==CHECK)begin if(!tap_idle278||read_pending336)tap_fault278<=1;tap_seen278<=0;end
   if(!invalidate_banks&&rs&&!rp&&ap>=24'h400800&&ap<24'h401800)begin
    if(!read_pending336)tap_fault278<=1;read_pending336<=0;
   end
   if(tap_capture278)begin tap_seen278<=1;
    if(!read359[33])tap_fault278<=1;else read_pending336<=1;
   end
  end
 end
 // One command handshake; the engine owns encoded bytes and RAM completion.
 assign exec_start298=0;assign exec_kind298=0;
 assign exec_op298=0;assign exec_length298=0;assign exec_data298=0;
 assign display_write=1'b0;
 assign display_request=state==DREQ&&display_request_ready&&!rst;
 assign ordinary_range=0;
 assign ordinary_first=unit336;assign ordinary_end300=12'd1;
 assign ordinary_byte=metadata313?held:qdata;
 assign ordinary_stream=0;
 assign ordinary_check=1'b0;
 assign ordinary_finish=header[0]==3&&state==MREAD313&&range_ready&&!rst&&!fault;
 assign ordinary_hash_start=0;
 assign ordinary_hash_kind=0;
 assign ordinary_hash_index=0;assign ordinary_hash_byte=0;
 assign mready=state==DREQ?display_request_ready:prelude_mode?context_ready:range_ready;
 assign context_valid=prelude_mode&&state==PUT&&!rst;assign context_data=held;
 assign begin_valid=state==BSTART&&range_ready&&!rst;
 assign begin_bank=identity[48];assign begin_raw=prelude_raw;
 assign range_first=unit336;assign range_count=12'd1;assign range_valid=0;
 assign range_dma_done=0;
 wire bv=state==DWAIT?display_response_valid:range_ready;
 wire [7:0] reply=display_response;
 assign display_response_ready=state==DWAIT&&!rst;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) wire [1:0] sealed_sync={2{sealed}};
 wire fv,fr;reg final_send,final_seen;
 nes_native_mailbox206 #(.WIDTH(1)) final_ack(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid(final_send),.src_ready(fr),.src_data(1'b1),.dst_valid(fv),.dst_ready(1'b1),.dst_data());
 assign host_ack278=final_send&&fr&&!rst;
 assign display_ack=fv&&!rst;assign retired=final_seen&&core_idle&&!rst;
 always @(posedge nes_clk or posedge rst)begin
  if(rst)final_seen<=0;else if(identity_valid&&identity_ready)final_seen<=0;else if(display_ack)final_seen<=1;
 end
 reg [31:0] written,last_map_token;reg [3:0] mask;reg map_receipt;
 wire [31:0] visible_token=chunk_ready?chunk_token:last_map_token;
 wire consume_write=!invalidate_banks&&write_end&&ap==(data_command278?24'h006059:24'h006050);
 wire good_consume=tap_idle278&&!read_pending336&&range_ready&&chunk_ready&&read_count==chunk_length&&dp==8'ha5&&mask==15&&written==chunk_token;
 assign tile_consume=consume_write&&good_consume&&owner==TILE&&!rst&&!fault;
 assign map_consume=state==CONSUME&&owner==MAP&&!rst&&!fault;
 assign jobs_committed336=!chunk_ready&&tap_idle278&&!read_pending336&&!rst&&!fault;
 assign staged=chunk_ready&&!fault&&!rst;assign receipt_committed=map_receipt&&!fault&&!rst;
 assign fault=failed||qfault||tfault||tap_fault278; // aperture error pulses are latched below
 reg [7:0] control;
 always @*begin
  control=0;
  case(address[7:0])
   8'h00:control=ordinary_ready;8'h01:control={fault||rst,invalidate_banks,6'd0};8'h04:control=qlen[7:0];8'h05:control={7'd0,qlen[8]};
   8'h40:control=chunk_ready&&(owner==TILE||state==DMA);
   8'h41:control={5'd0,identity[48],owner==MAP,tkind&&owner==TILE};
   8'h42:control=chunk_length[7:0];8'h43:control={4'd0,chunk_length[11:8]};
   8'h44:control=owner==MAP?first[7:0]:tslot[7:0];8'h45:control=owner==MAP?{4'd0,first[11:8]}:{6'd0,tslot[9:8]};
   8'h46:control=identity[39:32];8'h47:control=identity[47:40];
   8'h48:control=visible_token[7:0];8'h49:control=visible_token[15:8];8'h4a:control=visible_token[23:16];8'h4b:control=visible_token[31:24];
   8'h53:control=state==DMA&&batch?remaining:0;

   8'h60:control={7'd0,zero325};8'h61:control=header[1];
   8'h62:control=destination325[7:0];8'h63:control=destination325[15:8];
   8'h64:control=chunk_length[7:0];8'h65:control={4'd0,chunk_length[11:8]};
   8'h66:control=ppu325[7:0];8'h67:control=ppu325[15:8];
   8'h68:control={7'd0,identity[48]};
   8'h54:control=state==DPRESENT;8'h51:control=receipt_committed;8'h52:control=sealed_sync[1];
   default:;
  endcase
 end
 assign data_out=display_address ? held : address[23:8]==16'h0060 ? control : aperture_data;
 assign bus_valid=!read_n&&write_n&&(status_address||(!rst&&!fault&&!invalidate_banks&&((address[23:8]==16'h0060&&(!display_address||(state==DPRESENT&&sealed_sync[1]&&manifest_phase==2)))||
  !aoe)));

 // Asynchronous assertion survives a short STOP; acknowledgement is local to
 // the existing synchronized SNES write observer, never an unsynchronized bus.
 always @(posedge host_clk or posedge rst)begin
  if(rst)invalidate_banks<=1;
  else if(fault)invalidate_banks<=1;
  else if(write_end&&ap==24'h006006&&dp==8'ha5)invalidate_banks<=0;
 end
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin
   state<=IDLE;owner<=NONE;failed<=0;run_left313<=0;run_zero313<=0;manifest_byte313<=0;display_byte313<=0;requirements_complete313<=0;map_received313<=0;tiles_closed<=0;have_identity<=0;admitted286<=0;at<=0;held<=0;parser_address<=0;qretire<=0;packet_seq<=0;
   prelude_mode<=0;prelude_done<=0;begun<=0;batch<=0;active305.left<=0;cursor<=0;active305.token<=0;last_map_token<=0;map_receipt<=0;
   am<=0;asyn<=0;ap<=0;qtag<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;
   scroll_length<=0;ordinary_reads<=0;tile_proven<=0;seed325<=0;expanded325<=0;zero325<=0;
   written<=0;mask<=0;read_count<=0;final_send<=0;
   // Header bytes are read completely before use; no payload/header reset.
  end else begin
   am<=address;asyn<=am;ap<=asyn;qtag<=asyn;dm<=data_in;ds<=dm;dp<=ds;wm<=write_n;ws<=wm;wp<=ws;rm<=read_n;rs<=rm;rp<=rs;

   qretire<=0;if(final_send&&fr)final_send<=0;
   if(pe||ce||tfault||qfault)failed<=1;
   if(record_valid312&&!fault)begin
    if(state!=HLOAD315)failed<=1;
    else case(record_at312)
     0:begin active305.op<=record_byte312;active305.token<=0;active305.left<=0;end
     1:active305.section<=record_byte312;
     2:if(record_byte312!=packet_seq[7:0])failed<=1;
     3:if(record_byte312!=packet_seq[15:8])failed<=1;
     4:active305.start[7:0]<=record_byte312;5:active305.start[15:8]<=record_byte312;
     6:active305.span[7:0]<=record_byte312;7:active305.span[15:8]<=record_byte312;
     8:active305.encoded[7:0]<=record_byte312;9:active305.encoded[15:8]<=record_byte312;
     10:active305.token[7:0]<=record_byte312;11:active305.token[15:8]<=record_byte312;
     12:active305.token[23:16]<=record_byte312;13:active305.token[31:24]<=record_byte312;
     14:active305.left<=record_byte312;
     default:;
    endcase
   end
   if(iv&&can_admit)begin
    if(idata[31:0]<=last_serial)failed<=1;
    else begin admitted286<=full_idata278;have_identity<=1;requirements_complete313<=0;map_received313<=0;prelude_done<=0;begun<=0;prelude_mode<=0;tiles_closed<=0;packet_seq<=0;state<=IDLE;map_receipt<=0;last_map_token<=0;end
   end
   if(!failed&&!qfault&&!tfault)begin
    if(tiles_closed&&trequest)failed<=1;
    if(owner==NONE&&have_identity&&state!=DONE)begin
     if(state==OPEN)owner<=MAP;
     else if(trequest)begin owner<=TILE;end
    end
    if(owner==TILE)begin
     if(tend)tiles_closed<=1;
     if(range_idle295&&!chunk_ready&&!(header[0]==7&&state!=IDLE))begin owner<=NONE;end
     if(chunk_ready&&tgen!=identity[47:32])failed<=1;
    end
    if(tile_consume)begin
     if(state!=DMA||header[0]!=7||token!=chunk_token)failed<=1;
     else state<=SEND;
    end
    if(!invalidate_banks&&rs&&!rp&&display_read)begin
     if(state!=DPRESENT||manifest_phase!=2||!sealed_sync[1]||at>=12||ap!=24'h006070+at)failed<=1;
     else begin at<=at+1'b1;if(at==11)state<=IDLE;else state<=DREQ;end
    end
    if(consume)read_count<=0;
    if(!invalidate_banks&&rs&&!rp&&ap>=24'h400800&&ap<24'h401800)begin
     if(!chunk_ready||read_count>=chunk_length||ap!=24'h400800+read_count)failed<=1;
     else read_count<=read_count+1'b1;
    end
    if(!invalidate_banks&&write_end)begin
     if(ap>=24'h00604c&&ap<=24'h00604f)begin written[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;end
     if((ap==24'h006050&&data_command278)||(ap==24'h006059&&!data_command278))failed<=1;
     if(consume_write)begin
      mask<=0;if(!good_consume||(owner!=TILE&&state!=DMA))failed<=1;
      else if(owner==MAP)state<=data_command278?WAIT_RECEIPT:SEND;
     end
     if(ap==24'h006058)begin
      mask<=0;
      if(state!=IDLE||owner!=NONE||!storage_empty312||trequest||!map_receipt||!sealed_sync[1]||at!=12||dp!=8'h5a||mask!=15||written!=last_map_token)failed<=1;
      else begin final_send<=1;state<=DONE;end
     end
    end
    case(state)
     DREQ:if(mready)state<=DWAIT;
     DWAIT:if(bv)begin held<=reply;state<=DPRESENT;end
     DPRESENT:begin end
     IDLE:if(manifest_phase==2&&sealed_sync[1]&&at<12)state<=DREQ;
      else if(qr&&have_identity&&!qretire)begin
       at<=0;state<=HLOAD315;
      end
     HLOAD315:begin
      if(at==(header[0]==14?15:header[0]==12?14:10))state<=HCHECK315;
      else at<=at+1'b1;
     end
     HCHECK315:begin qlen<=queue_length312;at<=0;state<=CHECK;end
     CHECK:begin
      active305.endpos<=decode_end305;
      if(header[0]==0||header[0]>15||((header[0]==12||header[0]==14)&&header[1]!={7'd0,identity[48]})||packet_seq==16'hffff)failed<=1;
      else if(header[0]==13)begin
       if(prelude_done||begun||qlen!=48||header[1]!=5||{header[13],header[12]}!=32||
          {header[11],header[10]}!=0||{header[15],header[14]}!=0)failed<=1;
       else begin prelude_mode<=1;active305.span<=32;at<=0;parser_address<=16;state<=PREAD;end
      end
      else if(!prelude_done||(header[0]==1?begun:!begun))failed<=1;
      else if(header[0]==1)begin
       if(qlen!=28||header[1]!=0||{header[13],header[12]}!=12||
          {header[11],header[10]}!=0||{header[15],header[14]}!=0)failed<=1;
       else begin batch<=0;at<=0;parser_address<=16;state<=PREAD;end
      end
      else if(header[0]==14)begin
       if(qlen<26||{header[13],header[12]}!={7'd0,qlen}-16'd16||header[14]!=0||header[15]!=0||
        header[20]==0||header[20]>47||{header[19],header[18],header[17],header[16]}>32'hffffffff-{24'd0,header[20]})failed<=1;
       else begin batch<=1;cursor<=21;parser_address<=21;at<=0;
        map_receipt<=0;state<=DREAD;end
      end
      else if(header[0]==15||header[0]==10||header[0]==11||header[0]==3)begin
       if(plen+16'd16!={7'd0,qlen}||bad_internal305)failed<=1;else state<=XBEGIN298;
      end
      else if(header[0]!=12)begin
       if(!data_command278&&header[0]!=7)failed<=1;
       else        if({header[13],header[12]}+16'd16!={7'd0,qlen}||(data_command278&&bad_data278)||(header[0]==7&&bad_tile305))failed<=1;
       else if(data_command278)begin
        batch<=0;active305.token<=ordinary_next313;state<=OPEN;
       end else begin batch<=0;at<=0;parser_address<=16;state<=PREAD;end
      end
      else if(header[11]>7||header[15]!=0||header[14]==0||header[14]>64||header[14][0]||
       {header[13],header[12]}!=header[14]+16'd4||qlen!=header[14]+9'd20||
       {header[11],header[10]}+({8'd0,header[14]}>>1)>2048)failed<=1;
      else begin batch<=0;active305.start<={startpos[14:0],1'b0};
       state<=OPEN;map_receipt<=0;end
     end
     DREAD:state<=DCAP;
     DCAP:begin
      case(at)
       0:active305.start[7:0]<=qdata;1:active305.start[15:8]<=qdata;
       2:active305.span<={8'd0,qdata};default:;
      endcase cursor<=cursor+1'b1;parser_address<=parser_address+1'b1;
      if(at==2)state<=DCHECK;else begin at<=at+1'b1;state<=DREAD;end
     end
     DCHECK:begin
      if(header[11]>15||header[10][0]||header[14]==0||header[14]>64||header[14][0]||
       {header[11],header[10]}+{8'd0,header[14]}>4096||
       cursor+{1'b0,header[14]}+(remaining>1?9'd5:9'd0)>qlen||
       (remaining==1&&cursor+{1'b0,header[14]}!=qlen))failed<=1;
      else begin 
       cursor<=cursor+{1'b0,header[14]};map_receipt<=0;state<=OPEN;end
     end
     OPEN:if(owner==MAP)begin
      if(data_command278?(ordinary_next313==32'hffffffff||token!=ordinary_next313):(token!=allocation||allocation==32'hffffffff))failed<=1;
      else if(begin_ready)begin seed325<=0;expanded325<=0;zero325<=0;at<=0;if(!batch)parser_address<=data_command278?16:20;state<=PREAD;end
     end
     PREAD:state<=PCAP;
     PCAP:begin
      if(header[0]==1)begin
       case(at)
        0:if(qdata!=8'h72)failed<=1;
        1:if(qdata!=8'h24)failed<=1;
        2:if(qdata!={7'd0,identity[48]})failed<=1;
        4,5,6,7:if(qdata!=previous_serial313[8*(at-4)+:8])failed<=1;
        8:if(qdata!=1)failed<=1;
        default:if(qdata!=0)failed<=1;
       endcase
       if(at==11)begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=BSTART;end
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else if(header[0]==7)begin
       active305.token[at[1:0]*8+:8]<=qdata;
       if(at==3)state<=TILEWAIT313;
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else if(repeat325&&!prelude_mode)begin
       seed325[at[1:0]*8+:8]<=qdata;
       if(at+1==plen)begin
        zero325<=header[0]==5&&header[1]==5&&startpos==21&&outlen==1100&&seed325[7:0]==0&&qdata==0;
        state<=EXPAND325;
       end else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else begin held<=qdata;state<=PUT;end
     end
     TILEWAIT313:if(owner==TILE&&chunk_ready)begin
      if(token!=chunk_token||header[1]!={7'd0,tkind}||length!=chunk_length||
         startpos!=({6'd0,tslot}<<(tkind?5:4)))failed<=1;
      else begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=DMA;end
     end
     PUT:if(prelude_mode?mready:put_ready)begin
      if(prelude_mode&&at==14)scroll_length[7:0]<=held;
      if(prelude_mode&&at==15)scroll_length[10:8]<=held[2:0];
      if(at+1==length)state<=prelude_mode?PREWAIT:SEAL;else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end end
     EXPAND325:if(put_ready)begin
      if(expanded325+1==output325)state<=SEAL;
      else expanded325<=expanded325+1'b1;
     end
     SEAL:begin
      if(batch&&remaining==1)begin qretire<=1;packet_seq<=packet_seq+1'b1;end
      state<=batch?DMA:RETIRE;
     end
     RETIRE:begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=DMA;end
     WAIT_RECEIPT:if(tap_idle278&&range_ready)state<=SEND;
     SEND:if(tap_idle278&&range_ready)state<=CONSUME;
     CONSUME:begin
      if(header[0]==12||header[0]==14)begin last_map_token<=token;map_receipt<=1;end
      if(batch&&remaining>1)begin active305.left<=remaining-1'b1;active305.token<=token+1'b1;at<=0;parser_address<=cursor[7:0];state<=DREAD;end
      else begin owner<=header[0]==7&&(!range_idle295||chunk_ready)?TILE:NONE;
       if(batch)begin state<=IDLE;end
       else state<=IDLE;
      end
     end
     PREWAIT:begin
      prelude_mode<=0;prelude_done<=1;qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;
     end
     BSTART:if(mready)state<=BWAIT;
     BWAIT:if(range_ready)begin begun<=1;state<=IDLE;end
     BRET:state<=IDLE;
     XBEGIN298:if(range_ready)begin
      run_left313<=0;run_zero313<=0;parser_address<=16;
      manifest_byte313<=(header[0]==15||header[0]==3)?0:manifest_at;
      state<=MREAD313;
     end
     XWAIT298:if(range_ready)begin
      if(header[0]==12||header[0]==14||header[0]==7||data_command278)state<=CONSUME;
      else begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;end
     end
     MREAD313:if(header[0]!=3)state<=MCAP313;else if(range_ready)state<=MSEALWAIT313;
     MCAP313:begin
      if({1'b0,parser_address}>=qlen)failed<=1;
      else if((header[0]==11&&parser_address==16)||(requirements313&&parser_address==40))begin
       if(qdata!=(requirements313?1:3)||qlen<(requirements313?42:18))failed<=1;
       else begin parser_address<=parser_address+1'b1;state<=MREAD313;end
      end else if(rle313&&run_left313==0)begin
       if(run_end313>(requirements313?166:256)||
          (!qdata[7]&&{1'b0,parser_address}+{2'd0,qdata[6:0]}+9'd2>qlen))failed<=1;
       else begin run_left313<={1'b0,qdata[6:0]}+1'b1;run_zero313<=qdata[7];
        parser_address<=parser_address+1'b1;state<=MNEXT313;end
      end else begin
       held<=qdata;parser_address<=parser_address+1'b1;
       display_byte313<=header[0]==15&&parser_address<40;
       if(rle313)run_left313<=run_left313-1'b1;
       state<=MISSUE313;
      end
     end
     MISSUE313:if(range_ready)begin
      if(!canonical_read313&&canonical_bad332)failed<=1;
      else state<=MWAIT313;
     end
     MWAIT313:if(range_ready)begin
      begin
       if(!display_byte313)manifest_byte313<=manifest_byte313+1'b1;
       state<=MNEXT313;
      end
     end
     MNEXT313:begin
      if(run_zero313&&run_left313!=0)begin
       held<=0;display_byte313<=0;run_left313<=run_left313-1'b1;state<=MISSUE313;
      end else if({1'b0,parser_address}==qlen)begin
       if(run_left313!=0||(header[0]==15&&manifest_byte313!=166))failed<=1;
       else state<=MDONE313;
      end else state<=MREAD313;
     end
     MDONE313:begin
      if(header[0]==15)requirements_complete313<=1;
      else if(header[0]==10||header[0]==11)map_received313<=manifest_byte313;
      qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;
     end
     MSEALWAIT313:if(sealed)begin at<=0;state<=MDONE313;end

     default:;
    endcase
   end
  end
 end
endmodule
