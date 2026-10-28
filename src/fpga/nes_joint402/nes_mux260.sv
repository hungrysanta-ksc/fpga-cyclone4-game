// SPDX-License-Identifier: MIT
// Bounded integration. SHARED=0 is the identical serialized schedule with
// separate tile/map apertures, for a like-for-like RAM/control comparison.
module nes_output260 #(parameter SHARED=1,parameter [31:0] INITIAL_TOKEN=1)(output wire [5:0] ctx_address375,output wire ctx_write375,output wire [7:0] ctx_data375,input wire tag_write400,input wire[3:0]tag_at400,input wire[7:0]tag_data400,output wire tag_ready400,
 input wire hint_metaactive398,input wire[3:0]hint_meta_at398,output wire[7:0]hint_meta_q398,
 input wire footer_request396,input wire[7:0] footer_data396,
 output wire footer_capture396,output wire[2:0] footer_index396,output wire[7:0] footer_address396,
 input wire [7:0] ctx_q375,output wire [33:0] read359,input wire ready359,private359,
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
 input wire [153:0] link270,output wire [199:0] status270,output wire crc_take270,

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
// SPDX-License-Identifier: MIT
// Common final-record execution. The declaration comes from the retained
// board interface; no legacy parser, descriptor builder or context FSM lives
// behind this implementation. Physical CDC/read/CRC/credit are retained.
// SPDX-License-Identifier: MIT
// The host protocol is bytecode. This layer owns only physical IO handshakes,
// the immutable lease, and exact bus/token/CRC events.
 wire rst=reset||cancel;
 reg footer_phase396;reg[2:0] footer_at396;
 wire footer_active396=footer_request396;
 assign footer_index396=footer_at396;assign footer_address396=8'd250+footer_at396;
 assign footer_capture396=footer_active396&&footer_phase396&&!rst&&!fault;
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin footer_phase396<=0;footer_at396<=0;end
  else if(!footer_active396)begin footer_phase396<=0;footer_at396<=0;end
  else if(!footer_phase396)footer_phase396<=1;
  else begin footer_phase396<=0;footer_at396<=footer_at396==5?0:footer_at396+1'b1;end
 end
 typedef enum logic[5:0] {IDLE,HREAD,HCAP,CHECK,RREAD,RCAP,RCHECK,OPEN,GET,CAP,PUT,SEED,EXPAND,SEAL,EXPOSE,WAITREAD,TAKE,
  TILECHECK,TILEREAD,TILEPUT,CONTEXT,BEGINWAIT,MREAD,MCAP,MEMIT,MNEXT,MFINISH,ENDWAIT,DREQUEST,DWAIT,DVIEW,DONE,RVALIDATE} state_t;
 state_t state;
 wire [83:0] admitted286;wire [48:0] identity=admitted286[48:0];wire iv,admit_ready;
 reg nes_admitted,have_identity,failed,invalidate_banks,prelude_done,begun,tiles_closed,requirements_complete313;
 reg [31:0] allocation,last_serial,chunk_token,fence;
 wire [83:0] full_idata278=admitted286;
 wire can_admit=init278&&(!have_identity||state==DONE);
 nes_native_mailbox206 #(.WIDTH(84)) admission(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
  .src_valid(identity_valid&&!nes_admitted),.src_ready(admit_ready),.src_data({epoch278,raw278,bank,generation,serial}),
  .dst_valid(iv),.dst_ready(can_admit),.dst_data(admitted286));
 assign identity_ready=admit_ready&&!nes_admitted&&!rst;
 assign grant278=iv&&can_admit&&!rst;assign grant_epoch278=admitted286[83:52];assign grant_raw278=admitted286[51:49];
 assign grant_serial278=identity[31:0];assign grant_generation278=identity[47:32];
 always @(posedge nes_clk or posedge rst)if(rst)nes_admitted<=0;else if(identity_valid&&identity_ready)nes_admitted<=1;else if(display_ack)nes_admitted<=0;
 wire allocate;
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin allocation<=INITIAL_TOKEN;last_serial<=0;end
  else if(!rst)begin
   if(allocate&&allocation!=32'hffffffff)allocation<=allocation+1'b1;
   if(grant278&&identity[31:0]>last_serial)last_serial<=identity[31:0];
  end
 end
 assign next_token=allocation;
 reg [7:0] op,flags,at,held;reg [8:0] parser_address,qlen,bodylen;
 reg [95:0] record394;
 wire [15:0] destination=record394[15:0],store=record394[31:16],decoded=record394[47:32],canonical=record394[95:80];
 wire [7:0] attributes=record394[55:48],wbank=record394[63:56],vmain=record394[71:64],region=record394[79:72];
 wire [1:0] mode=attributes[3:2];wire reference=attributes[4],stride32=attributes[5],zero_tail=attributes[6];
 wire [16:0] encoded_size=reference||mode==0?17'd0:mode==1?{1'b0,decoded}:mode==3?17'd4:17'd2;
 reg active_fragment,first_fragment,last_fragment,payload_phase;reg [15:0] offset,fragment_at,source_total;
 reg[11:0]chunk_length,produced;wire[11:0]read_count;wire[15:0]tap_position;reg[15:0]tap_base402;
 reg [31:0] seed;reg [2:0] seed_left;reg [7:0] records_left;
 reg [8:0] record_cursor,payload_cursor;
 reg [7:0] qretire_delay;reg qretire,consume_record312;
 wire qr,qfault,storage_empty312;wire [8:0] queue_length312;wire [7:0] qdata;
 reg [8:0] canonical_address;reg canonical_write;
 wire [127:0] progress_status={5'd0,1'b0,staged,tiles_closed,
  (staged?chunk_token[7:0]:allocation[7:0]),(staged?chunk_token[15:8]:allocation[15:8]),
  (staged?chunk_token[23:16]:allocation[23:16]),(staged?chunk_token[31:24]:allocation[31:24]),32'd0,
  chunk_length[7:0],4'd0,chunk_length[11:8],5'd0,identity[48],1'b0,region==1,
  canonical[7:0],canonical[15:8],identity[39:32],identity[47:40]};
 nes_queue260 queue(.irq398(),.control_write398(1'b0),.control_address398(8'd0),.control_q398(),.admit319(queue_admit319),.expected_select313(canonical_write||(state==ENDWAIT)),
  .expected_write313(canonical_write),.expected_address313(state==ENDWAIT?expected_addr332:canonical_address),.expected_data313(held),
  .frame_start312(grant278),.frame_serial312(identity[31:0]),.frame_generation312(identity[47:32]),.record312(192'd0),.load_enable312(1'b0),.load_at315(4'd0),
  .storage_empty312(storage_empty312),.record_valid312(),.record_at312(),.record_byte312(),.link270(link270),.status270(status270),.crc_take270(crc_take270),
  .progress_status(progress_status),.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(selected),.miso(miso),.sn_address(parser_address[7:0]),.sn_data(qdata),.packet_ready(qr),.packet_length(queue_length312),
  .parser_retire(qretire),.consume_record312(consume_record312),.fault(qfault));
 assign expected_data332=qdata;
 assign ctx_address375=0;assign ctx_write375=0;assign ctx_data375=0;
 wire begin_ready,put_ready,chunk_ready,pe,ce,aoe,tile_empty396;wire [7:0] aperture_data,tile_q;reg [10:0] scroll_length;
 wire aperture_begin=state==OPEN&&!reference&&!footer_active396;
 wire aperture_put=!footer_active396&&((state==PUT&&op!=8'had)||state==EXPAND);
 wire [7:0] aperture_byte=state==EXPAND?seed[(produced[1:0]&(mode==3?2'd3:2'd1))*8+:8]:held;
 wire consume=state==TAKE&&!reference&&!footer_active396;
 wire word_valid,word_ready,word_end,word_partial,word_kind;wire [15:0] word_generation;wire [9:0] word_slot;wire [5:0] word_length;
 wire [9:0] stage_address402;wire stage_write402;wire[7:0]stage_data402;wire stage_atomic402;
 wire tag_grant402=tag_write400&&!stage_atomic402&&!rst&&!fault;assign tag_ready400=tag_grant402;
 wire[9:0]meta_address396=tag_grant402?10'd928+tag_at400:stage_address402;wire meta_write396=tag_grant402||stage_write402;wire[7:0]meta_data396=tag_grant402?tag_data400:stage_data402;wire tile_fault;
 nes_tile_link394 tile_link(.hint_metaactive398(hint_metaactive398),.hint_meta_at398(hint_meta_at398),.hint_meta_q398(hint_meta_q398),.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.source_fault(fault),
  .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
  .end_valid(end_valid),.end_partial(end_partial295),.end_ready(end_ready),.end_generation(end_generation),
  .word_valid(word_valid),.word_ready(word_ready),.word_end(word_end),.word_partial(word_partial),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),
  .read_at(meta_address396),.meta_write(meta_write396),.meta_data(meta_data396),.read_data(tile_q),.fault(tile_fault));
 nes_stage396 aperture(.meta_pause398(tag_grant402),.meta_atomic398(stage_atomic402),.clk(host_clk),.reset(rst),.active(!fault&&have_identity),.begin_valid(aperture_begin),.begin_tile(mode==0),.begin_length(chunk_length),.begin_token(allocation),
  .generation(identity[47:32]),.kind(region==1),.first(canonical[9:0]),.begin_ready(begin_ready),.byte_valid(aperture_put),.byte_data(aperture_byte),.byte_ready(put_ready),.seal(state==SEAL&&!footer_active396),
  .producer_error(pe),.chunk_ready(chunk_ready),.consume(consume),.consume_token(chunk_token),.consume_error(ce),.tile_empty(tile_empty396),
  .word_valid(word_valid),.word_end(word_end),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),.word_ready(word_ready),
  .meta_address(stage_address402),.meta_write(stage_write402),.meta_data(stage_data402),.meta_q(tile_q),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe));
 wire accept_end=word_valid&&word_end&&word_ready;
 assign tile_closed267=tiles_closed;
 assign allocate=!footer_active396&&((state==OPEN&&(reference||begin_ready))||(state==ENDWAIT&&sealed));
 // Bounds are derived independently from immutable admission, not from ARM's
 // receipt declarations. MAP REF is forbidden; no unchanged holes are legal.
 wire bad_record,checked396;
 nes_check396 record_check(.clk(host_clk),.reset(rst),.start(state==RCHECK&&!footer_active396),.bank(identity[48]),.record(record394),.done(checked396),.bad(bad_record));
 // Physical response capture is separate from the synchronized release edge.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg wm,ws,rm,rs;
 reg wp,rp;reg [23:0] ap;reg [7:0] dp;
 wire tap_seen,read_pending,tap_fault;wire[7:0]read_data402;wire read_event402;wire data_address=address>=24'h400800&&address<24'h401800;
 wire capture=state==WAITREAD&&!reference&&chunk_ready&&!tap_seen&&!read_n&&write_n&&data_address&&bus_valid&&!invalidate_banks;
 wire [3:0] read_op=region==2?4'd14:region<2?4'd7:4'd2;
 wire crc_byte=region==5&&!zero_tail&&(tap_position<scroll_length||(grant_raw278!=0&&tap_position>=3169));
 wire crc_start=tap_position==0||(tap_position>=3169&&(tap_position-16'd3169)%16==0);
 wire read_end;
 assign read359={read_event402,crc_byte,crc_start,read_op,region[2:0],tap_position,read_data402};
 nes_read_owner400 read_owner(.clk(host_clk),.reset(rst),.stop(fault),.active(state==WAITREAD),
  .start(state==OPEN&&(reference||begin_ready)&&!footer_active396),.clear(state==TAKE),.read_n(read_n),.capture(capture),
  .ended(read_end&&ap>=24'h400800&&ap<24'h401800&&!invalidate_banks),.checker_ready(ready359),
  .address(address),.ended_address(ap),.data(aperture_data),.token(chunk_token),.length(chunk_length),
  .base_position(tap_base402),.map_stride(region==2&&stride32),.count(read_count),.position(tap_position),
  .held_data(read_data402),.seen(tap_seen),.pending(read_pending),.fault(tap_fault),.event_valid(read_event402));
 wire write_end=ws&&!wp&&rp;
 assign read_end=rs&&!rp;
 reg [31:0] written;reg [3:0] mask;reg [3:0] view_at;
 wire good_consume=state==WAITREAD&&read_count==chunk_length&&ready359&&!read_pending&&mask==15&&written==chunk_token&&dp==8'ha5;
 assign fault=failed||qfault||tile_fault||tap_fault;
 assign staged=state==WAITREAD&&!fault&&!rst;
 assign ordinary_ready=staged;
 assign receipt_committed=begun&&!fault&&!rst;
 assign jobs_committed336=!staged&&ready359&&!read_pending&&!active_fragment&&tile_empty396&&!rst&&!fault;
 assign crc_reset287=state==CHECK;
 assign ordinary_finish=!footer_active396&&state==ENDWAIT&&range_ready&&!sealed&&!rst&&!fault;
 assign context_valid=!footer_active396&&state==PUT&&op==8'had&&!rst&&!fault;assign context_data=held;
 assign begin_valid=!footer_active396&&state==BEGINWAIT&&range_ready&&!rst;assign begin_bank=identity[48];assign begin_raw=grant_raw278;
 assign display_write=0;assign display_request=!footer_active396&&state==DREQUEST&&display_request_ready&&!rst;
 assign display_response_ready=!footer_active396&&state==DWAIT&&!rst;
 assign range_valid=0;assign range_first=0;assign range_count=1;assign range_dma_done=0;
 assign ordinary_range=0;assign ordinary_first=0;assign ordinary_end300=1;assign ordinary_stream=0;assign ordinary_byte=held;assign ordinary_check=0;
 assign ordinary_hash_start=0;assign ordinary_hash_kind=0;assign ordinary_hash_index=0;assign ordinary_hash_byte=0;
 assign exec_start298=0;assign exec_kind298=0;assign exec_op298=0;assign exec_length298=0;assign exec_data298=0;
 reg final_send,final_seen;wire fr,fv;
 nes_native_mailbox206 #(.WIDTH(1)) final_ack(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),.src_valid(final_send),.src_ready(fr),.src_data(1'b1),.dst_valid(fv),.dst_ready(1'b1),.dst_data());
 assign host_ack278=final_send&&fr&&!rst;assign display_ack=fv&&!rst;assign retired=final_seen&&core_idle&&!rst;
 always @(posedge nes_clk or posedge rst)if(rst)final_seen<=0;else if(identity_valid&&identity_ready)final_seen<=0;else if(display_ack)final_seen<=1;
 reg [8:0] meta_at,map_received313;reg [7:0] run_left;reg run_zero;reg meta_display;
 wire [7:0] header[0:1];assign header[0]=op;assign header[1]=region;
 reg [7:0] control;
 always @*begin
  control=0;
  if(address[7:0]>=8'h80&&address[7:0]<8'h8c)control=record394[(address[3:0])*8+:8];
  else case(address[7:0])
   8'h00,8'h40:control=staged;
   8'h01:control={fault||rst,invalidate_banks,6'd0};
   8'h48,8'h49,8'h4a,8'h4b:control=(state==WAITREAD?chunk_token:fence)>>(address[1:0]*8);
   8'h54:control=state==DVIEW;8'h51:control=receipt_committed;8'h52:control=sealed;
   8'h8c:control=fragment_at[7:0];8'h8d:control=fragment_at[15:8];8'h8e:control=chunk_length[7:0];8'h8f:control={4'd0,chunk_length[11:8]};
   8'h90:control={6'd0,last_fragment,first_fragment};
   8'h91,8'h92,8'h93,8'h94:control=identity[31:0]>>((address[2:0]-1)*8);
   8'h95:control=identity[39:32];8'h96:control=identity[47:40];8'h97:control={7'd0,identity[48]};8'h98:control=identity[31:0]<=2;
   8'h99:control=begun&&state!=DONE;
   default:;
  endcase
 end
 wire display_address=address>=24'h006070&&address<24'h00607c;
 assign data_out=display_address ? held : address[23:8]==16'h0060 ? control : aperture_data;
 assign bus_valid=!read_n&&write_n&&(address==24'h006001||(!rst&&!fault&&!invalidate_banks&&
  ((address[23:8]==16'h0060&&(!display_address||state==DVIEW))||(!aoe&&state==WAITREAD))));
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin
   state<=IDLE;have_identity<=0;failed<=0;invalidate_banks<=1;prelude_done<=0;begun<=0;tiles_closed<=0;requirements_complete313<=0;
   op<=0;flags<=0;at<=0;held<=0;parser_address<=0;qlen<=0;bodylen<=0;record394<=0;active_fragment<=0;first_fragment<=0;last_fragment<=0;payload_phase<=0;
   offset<=0;fragment_at<=0;source_total<=0;chunk_length<=0;produced<=0;tap_base402<=0;seed<=0;seed_left<=0;records_left<=0;record_cursor<=0;payload_cursor<=0;
   qretire<=0;qretire_delay<=0;consume_record312<=0;canonical_address<=0;canonical_write<=0;chunk_token<=0;fence<=0;
   am<=0;asyn<=0;ap<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;
   written<=0;mask<=0;view_at<=0;final_send<=0;scroll_length<=0;meta_at<=0;map_received313<=0;run_left<=0;run_zero<=0;meta_display<=0;
  end else begin
   am<=address;asyn<=am;ap<=asyn;dm<=data_in;ds<=dm;dp<=ds;wm<=write_n;ws<=wm;wp<=ws;rm<=read_n;rs<=rm;rp<=rs;
   qretire<=0;consume_record312<=0;canonical_write<=0;qretire_delay<={qretire_delay[6:0],qretire};
   if(final_send&&fr)final_send<=0;
   if(pe||ce)failed<=1;
   if(fault)invalidate_banks<=1;
   if(grant278)begin
    if(identity[31:0]<=last_serial)failed<=1;
    else begin have_identity<=1;prelude_done<=0;begun<=0;tiles_closed<=0;requirements_complete313<=0;map_received313<=0;active_fragment<=0;state<=IDLE;view_at<=0;end
   end
   if(accept_end)begin if(word_generation!=identity[47:32])failed<=1;else if(!word_partial)tiles_closed<=1;end
   if(write_end)begin
    if(ap==24'h00606f&&dp==8'hee)failed<=1;
    if(ap==24'h006006&&dp==8'ha5)invalidate_banks<=0;
    if(!invalidate_banks)begin
     if(ap>=24'h00604c&&ap<=24'h00604f)begin written[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;end
     if(ap==24'h006050)begin mask<=0;if(!good_consume)failed<=1;else state<=TAKE;end
     if(ap==24'h006058)begin
      mask<=0;if(state!=IDLE||!storage_empty312||active_fragment||!sealed||view_at!=12||dp!=8'h5a||mask!=15||written!=fence)failed<=1;
      else begin final_send<=1;state<=DONE;end
     end
    end
   end
   if(read_end&&ap>=24'h006070&&ap<24'h00607c&&!invalidate_banks)begin
    if(state!=DVIEW||ap!=24'h006070+view_at||view_at>=12||!sealed)failed<=1;
    else begin view_at<=view_at+1'b1;state<=view_at==11?IDLE:DREQUEST;end
   end
   if(!fault&&!footer_active396)case(state)
    IDLE:if(qr&&have_identity&&!qretire&&!qretire_delay)begin at<=0;parser_address<=0;state<=HREAD;end
    HREAD:state<=HCAP;
    HCAP:begin
     case(at)0:op<=qdata;1:flags<=qdata;2:bodylen[7:0]<=qdata;3:bodylen[8]<=qdata[0];endcase
     if(at==3)begin qlen<=queue_length312;state<=CHECK;end
     else begin at<=at+1'b1;parser_address<=at==0?1:at==1?8:9;state<=HREAD;end
    end
    CHECK:begin
     at<=0;parser_address<=10;run_left<=0;run_zero<=0;payload_phase<=0;
     if(bodylen+10!=qlen||flags[7:4]!=0||sealed)failed<=1;
     else if(op==8'had)begin if(prelude_done||begun||flags!=5||bodylen!=32)failed<=1;else state<=GET;end
     else if(!prelude_done||(op==8'ha1 ? begun : !begun))failed<=1;
     else case(op)
      8'ha1:if(flags!=0||bodylen!=12)failed<=1;else state<=GET;
      8'h90,8'h91:begin
       if(active_fragment||bodylen<12||(op==8'h91&&(bodylen!=12||flags!=0)))failed<=1;
       else begin records_left<={4'd0,flags[3:0]}+1'b1;record_cursor<=10;payload_cursor<=10+12*({5'd0,flags[3:0]}+1'b1);state<=RREAD;end
      end
      8'h92:begin
       if(!active_fragment||flags!=0||bodylen<3)failed<=1;else state<=GET;
      end
      8'haf:begin if(active_fragment||requirements_complete313||flags>1||bodylen<25)failed<=1;else begin meta_at<=0;meta_display<=1;state<=MREAD;end end
      8'haa,8'hab:begin if(active_fragment||!requirements_complete313||flags!=2||bodylen<3)failed<=1;else state<=GET;end
      8'ha3:begin if(active_fragment||!requirements_complete313||map_received313!=256||bodylen!=0||flags!=0||!tiles_closed)failed<=1;else state<=ENDWAIT;end
      default:failed<=1;
     endcase
    end
    RREAD:state<=RCAP;
    RCAP:begin
     record394[at*8+:8]<=qdata;
     if(at==11)state<=RCHECK;else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=RREAD;end
    end
    RCHECK:state<=RVALIDATE;
    RVALIDATE:if(checked396)begin
     if(bad_record||allocation==32'hffffffff||payload_cursor>qlen)failed<=1;
     else begin
      offset<=0;fragment_at<=0;first_fragment<=1;last_fragment<=!(mode>1&&!zero_tail&&decoded>512);produced<=0;seed<=0;
      source_total<=zero_tail?16'd2:decoded;chunk_length<=reference?12'd0:zero_tail?12'd2:mode>1&&decoded>512?12'd512:decoded[11:0];
      tap_base402<=region<2?(canonical<<(region==1?5:4)):region==2?(canonical<<1):canonical;
      if(op==8'h91)begin
       if(mode!=1||reference||decoded<=234)failed<=1;
       else begin active_fragment<=1;qretire<=1;state<=IDLE;end
      end else begin
       parser_address<=payload_cursor;
       if(payload_cursor+encoded_size>qlen||(records_left==1&&payload_cursor+encoded_size!=qlen))failed<=1;
       else state<=OPEN;
      end
     end
    end
    GET:state<=CAP;
    CAP:begin
     if(op==8'ha1)begin
      if(qdata!=(at==0?8'h72:at==1?8'h24:at==2?{7'd0,identity[48]}:at>=4&&at<8?(identity[31:0]-1'b1)>>((at-4)*8):at==8?8'd1:8'd0))failed<=1;
      if(at==11)begin qretire<=1;state<=BEGINWAIT;end
      else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=GET;end
     end else if((op==8'h92&&!payload_phase)||op==8'haa||op==8'hab)begin
      if(at==0)begin held<=qdata;at<=1;parser_address<=11;state<=GET;end
      else if(op==8'h92)begin
       if({qdata,held}!=offset||{1'b0,offset}+bodylen-2>source_total||(region==2&&(offset[0]||bodylen[0])))failed<=1;
       else begin
        fragment_at<=offset;chunk_length<=bodylen-2;first_fragment<=offset==0;last_fragment<=offset+bodylen-2==source_total;payload_phase<=1;
        tap_base402<=region==2?(canonical<<1)+(stride32?(offset<<5):offset):(canonical<<(region==1?5:region==0?4:0))+offset;
        parser_address<=12;produced<=0;state<=OPEN;
       end
      end else begin
       if({qdata,held}!={7'd0,map_received313})failed<=1;
       else begin parser_address<=12;meta_at<=map_received313;meta_display<=0;state<=MREAD;end
      end
     end else begin held<=qdata;state<=op==8'had ? PUT : mode>1 ? SEED : PUT;end
    end
    OPEN:if(reference||begin_ready)begin
     if(allocation==32'hffffffff)failed<=1;
     else begin chunk_token<=allocation;mask<=0;at<=0;
      if(reference)begin if(records_left==1)qretire<=1;state<=EXPOSE;end
      else if(mode==0)begin if(records_left==1)qretire<=1;state<=EXPOSE;end else if(mode>1&&fragment_at!=0)state<=EXPAND;else state<=GET;
     end
    end
    PUT:if(op==8'had ? context_ready : put_ready)begin
     if(op==8'had&&at==14)scroll_length[7:0]<=held;
     if(op==8'had&&at==15)scroll_length[10:8]<=held[2:0];
     if(op==8'had ? at==31 : produced+1==chunk_length)begin
      if(op==8'had)begin prelude_done<=1;qretire<=1;state<=IDLE;end else state<=SEAL;
     end else begin at<=at+1'b1;produced<=produced+1'b1;parser_address<=parser_address+1'b1;state<=GET;end
    end
    SEED:begin
     seed[at[1:0]*8+:8]<=held;
     if(at==(mode==3?3:1))begin if(zero_tail&&(seed[7:0]!=0||held!=0))failed<=1;else state<=EXPAND;end
     else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=GET;end
    end
    EXPAND:if(put_ready)begin if(produced+1==chunk_length)state<=SEAL;else produced<=produced+1'b1;end
    SEAL:begin if((op==8'h92||records_left==1)&&!(mode>1&&fragment_at!=0))qretire<=1;state<=EXPOSE;end
    EXPOSE:if(reference||chunk_ready)state<=WAITREAD;
    WAITREAD:;
    TAKE:begin
     
     if(op!=8'h92&&mode>1&&!last_fragment)begin
      fragment_at<=fragment_at+chunk_length;chunk_length<=source_total-fragment_at-chunk_length>512?512:source_total-fragment_at-chunk_length;
      first_fragment<=0;last_fragment<=source_total-fragment_at-chunk_length<=512;produced<=0;state<=OPEN;
     end else if(op==8'h92)begin
      consume_record312<=1;offset<=offset+chunk_length;if(last_fragment)active_fragment<=0;state<=IDLE;
     end else if(records_left>1)begin
      records_left<=records_left-1'b1;record_cursor<=record_cursor+12;parser_address<=record_cursor+12;at<=0;
      payload_cursor<=payload_cursor+(mode==0||reference?0:mode==1?decoded:mode==3?4:2);state<=RREAD;
     end else begin consume_record312<=1;state<=IDLE;end
    end
    BEGINWAIT:if(range_ready)begin begun<=1;state<=IDLE;end
    MREAD:state<=MCAP;
    MCAP:begin
     if(parser_address>=qlen)failed<=1;
     else if((op==8'hab&&parser_address==12)||(op==8'haf&&flags==1&&parser_address==34))begin
      if(qdata!=(op==8'haf ? 1 : 3))failed<=1;else begin parser_address<=parser_address+1'b1;state<=MREAD;end
     end else if(((op==8'haf&&flags==1&&parser_address>34)||op==8'hab)&&run_left==0)begin
      if(meta_at+{2'd0,qdata[6:0]}+1>(op==8'haf ? 166 : 256)||(!qdata[7]&&parser_address+qdata[6:0]+2>qlen))failed<=1;
      else begin run_left<={1'b0,qdata[6:0]}+1'b1;run_zero<=qdata[7];parser_address<=parser_address+1'b1;state<=MNEXT;end
     end else begin
      held<=qdata;parser_address<=parser_address+1'b1;
      meta_display<=op==8'haf&&parser_address<34;
      if((op==8'haf&&flags==1&&parser_address>34)||op==8'hab)run_left<=run_left-1'b1;
      state<=MEMIT;
     end
    end
    MEMIT:begin
     canonical_address<=meta_display ? 9'd448+parser_address-11 : op==8'haf ? 9'd256+meta_at : meta_at;
     canonical_write<=1;state<=MFINISH;
    end
    MFINISH:begin if(!meta_display)meta_at<=meta_at+1'b1;state<=MNEXT;end
    MNEXT:if(run_zero&&run_left!=0)begin held<=0;meta_display<=0;run_left<=run_left-1'b1;state<=MEMIT;end
     else if(parser_address==qlen)begin
      if(run_left!=0||(op==8'haf&&meta_at!=166))failed<=1;
      else begin if(op==8'haf)requirements_complete313<=1;else map_received313<=meta_at;qretire<=1;state<=IDLE;end
     end else state<=MREAD;
    ENDWAIT:if(sealed)begin
     if(allocation==32'hffffffff)failed<=1;else begin fence<=allocation;qretire<=1;view_at<=0;state<=DREQUEST;end
    end
    DREQUEST:if(display_request_ready)state<=DWAIT;
    DWAIT:if(display_response_valid)begin held<=display_response;state<=DVIEW;end
    DVIEW:;
    default:;
   endcase
  end
 end

 wire[2:0]phase=state==WAITREAD?3'd1:state==ENDWAIT?3'd2:state==DVIEW?3'd3:state==DONE?3'd5:sealed&&view_at==12?3'd4:3'd0;
 wire finish_pending=state==ENDWAIT;
 // synthesis translate_off
`ifndef SYNTHESIS
 wire handler=0;wire[11:0]debug_pc=state;
`endif
 // synthesis translate_on
endmodule
