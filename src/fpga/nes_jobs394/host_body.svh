// SPDX-License-Identifier: MIT
// Common final-record execution. The declaration comes from the retained
// board interface; no legacy parser, descriptor builder or context FSM lives
// behind this implementation. Physical CDC/read/CRC/credit are retained.
 wire rst=reset||cancel;
 typedef enum logic[5:0] {IDLE,HREAD,HCAP,CHECK,RREAD,RCAP,RCHECK,OPEN,GET,CAP,PUT,SEED,EXPAND,SEAL,EXPOSE,WAITREAD,TAKE,
  TILECHECK,TILEREAD,TILEPUT,CONTEXT,BEGINWAIT,MREAD,MCAP,MEMIT,MNEXT,MFINISH,ENDWAIT,DREQUEST,DWAIT,DVIEW,DONE} state_t;
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
 reg [11:0] chunk_length,read_count,produced;reg [15:0] tap_position;
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
 nes_queue260 queue(.admit319(queue_admit319),.expected_select313(canonical_write||(state==ENDWAIT)),
  .expected_write313(canonical_write),.expected_address313(state==ENDWAIT?expected_addr332:canonical_address),.expected_data313(held),
  .frame_start312(grant278),.frame_serial312(identity[31:0]),.frame_generation312(identity[47:32]),.record312(192'd0),.load_enable312(1'b0),.load_at315(4'd0),
  .storage_empty312(storage_empty312),.record_valid312(),.record_at312(),.record_byte312(),.link270(link270),.status270(status270),.crc_take270(crc_take270),
  .progress_status(progress_status),.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(selected),.miso(miso),.sn_address(parser_address[7:0]),.sn_data(qdata),.packet_ready(qr),.packet_length(queue_length312),
  .parser_retire(qretire),.consume_record312(consume_record312),.fault(qfault));
 assign expected_data332=qdata;
 assign ctx_address375=0;assign ctx_write375=0;assign ctx_data375=0;
 wire begin_ready,put_ready,chunk_ready,pe,ce,aoe;wire [7:0] aperture_data,tile_q;reg [10:0] scroll_length;
 wire aperture_begin=state==OPEN&&!reference;
 wire aperture_put=(state==PUT&&op!=8'had)||state==EXPAND||state==TILEPUT;
 wire [7:0] aperture_byte=state==EXPAND?seed[(produced[1:0]&(mode==3?2'd3:2'd1))*8+:8]:state==TILEPUT?tile_q:held;
 wire consume=state==TAKE&&!reference;
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(host_clk),.reset(rst),.active(!fault),.stop(1'b0),
  .wide325(1'b1),.begin_valid(aperture_begin),.begin_length(chunk_length),.begin_token(allocation),.begin_ready(begin_ready),
  .byte_valid(aperture_put),.byte_data(aperture_byte),.byte_ready(put_ready),.seal(state==SEAL),.cancel(1'b0),.producer_error(pe),
  .chunk_ready(chunk_ready),.chunk_length(),.chunk_token(),.consume(consume),.consume_token(chunk_token),.consume_error(ce),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe),.dir());
 wire word_valid,word_ready,word_end,word_partial,word_kind;wire [15:0] word_generation;wire [9:0] word_slot;wire [5:0] word_length;
 reg [4:0] tile_at;reg [11:0] tile_bytes;
 wire tile_fault;
 nes_tile_link394 tile_link(.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.source_fault(failed||qfault),
  .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
  .end_valid(end_valid),.end_partial(end_partial295),.end_ready(end_ready),.end_generation(end_generation),
  .word_valid(word_valid),.word_ready(word_ready),.word_end(word_end),.word_partial(word_partial),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),
  .read_at(tile_at),.read_data(tile_q),.fault(tile_fault));
 wire accept_end=word_valid&&word_end&&(state!=TILEREAD&&state!=TILEPUT);
 assign word_ready=accept_end||(state==TILEPUT&&put_ready&&tile_at==word_length-1);
 assign tile_closed267=tiles_closed;
 assign allocate=(state==OPEN&&(reference||begin_ready))||(state==ENDWAIT&&sealed);
 // Bounds are derived independently from immutable admission, not from ARM's
 // receipt declarations. MAP REF is forbidden; no unchanged holes are legal.
 wire [16:0] last_byte={1'b0,canonical}+{1'b0,decoded};
 wire [16:0] store_end={1'b0,store}+{1'b0,decoded};
 reg bad_record;
 always @*begin
  bad_record=attributes[7]||decoded==0||region>5||canonical[15:13]!=0;
  case(region)
   0,1:;
   2:bad_record=bad_record||reference||zero_tail||mode!=1||attributes[1:0]!=0||decoded[0]||wbank!=8'h7e||store<16'hc000||store_end>17'hd000||
     canonical>=2048||(stride32?({1'b0,canonical[9:5]}+(decoded>>1)>32):({1'b0,canonical}+(decoded>>1)>2048))||vmain!=(stride32?8'h81:8'h80)||destination!=16'h3000+{identity[48],13'd0}+canonical;
   3,4,5:bad_record=bad_record||stride32||wbank!=8'h7f||vmain!=0||last_byte>(region==3?512:region==4?544:3418)||
    store!=(region==3?16'h6000:region==4?16'h6200:16'h6500)+{identity[48],15'd0}+canonical||
    (reference?(region==5||canonical!=0||mode!=0||decoded!=(region==3?512:544)||attributes[1:0]!=(region==3?1:2)):
      (attributes[1:0]!=3||mode==0||destination!=0))||
    (zero_tail&&(region!=5||canonical!=21||decoded!=1100||mode!=2));
   default:bad_record=1;
  endcase
  // Tile destination and count use the region's units; no old byte ABI.
  if(region==0)bad_record=attributes!=0||decoded==0||decoded[3:0]!=0||{1'b0,canonical}+{5'd0,decoded[15:4]}>1024||wbank!=8'h7e||vmain!=8'h80||store<16'h8000||store_end>17'ha000||destination!=(identity[48]?16'h6000:16'd0)+(canonical<<3);
  if(region==1)bad_record=attributes!=0||decoded==0||decoded[4:0]!=0||{1'b0,canonical}+{6'd0,decoded[15:5]}>128||wbank!=8'h7e||vmain!=8'h80||store<16'h8000||store_end>17'ha000||destination!=16'h2000+{identity[48],13'd0}+(canonical<<4);
 end
 // Physical response capture is separate from the synchronized release edge.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg wm,ws,rm,rs;
 reg wp,rp;reg [23:0] ap;reg [7:0] dp;
 reg tap_seen,read_pending,tap_fault;wire data_address=address>=24'h400800&&address<24'h401800;
 wire capture=state==WAITREAD&&!reference&&chunk_ready&&!tap_seen&&!read_n&&write_n&&data_address&&bus_valid&&!invalidate_banks;
 wire [3:0] read_op=region==2?4'd14:region<2?4'd7:4'd2;
 wire crc_byte=region==5&&!zero_tail&&(tap_position<scroll_length||(grant_raw278!=0&&tap_position>=3169));
 wire crc_start=tap_position==0||(tap_position>=3169&&(tap_position-16'd3169)%16==0);
 assign read359={capture&&ready359&&!read_pending&&address==24'h400800+read_count&&read_count<chunk_length&&!fault&&!rst,
  crc_byte,crc_start,read_op,region[2:0],tap_position,aperture_data};
 wire write_end=ws&&!wp&&rp;
 wire read_end=rs&&!rp;
 reg [31:0] written;reg [3:0] mask;reg [3:0] view_at;
 wire good_consume=state==WAITREAD&&read_count==chunk_length&&ready359&&!read_pending&&mask==15&&written==chunk_token&&dp==8'ha5;
 assign fault=failed||qfault||tile_fault||tap_fault;
 assign staged=state==WAITREAD&&!fault&&!rst;
 assign ordinary_ready=staged;
 assign receipt_committed=begun&&!fault&&!rst;
 assign jobs_committed336=!staged&&ready359&&!read_pending&&!active_fragment&&!rst&&!fault;
 assign crc_reset287=state==CHECK;
 assign ordinary_finish=state==ENDWAIT&&range_ready&&!sealed&&!rst&&!fault;
 assign context_valid=state==PUT&&op==8'had&&!rst&&!fault;assign context_data=held;
 assign begin_valid=state==BEGINWAIT&&range_ready&&!rst;assign begin_bank=identity[48];assign begin_raw=grant_raw278;
 assign display_write=0;assign display_request=state==DREQUEST&&display_request_ready&&!rst;
 assign display_response_ready=state==DWAIT&&!rst;
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
   offset<=0;fragment_at<=0;source_total<=0;chunk_length<=0;read_count<=0;produced<=0;tap_position<=0;seed<=0;seed_left<=0;records_left<=0;record_cursor<=0;payload_cursor<=0;
   qretire<=0;qretire_delay<=0;consume_record312<=0;canonical_address<=0;canonical_write<=0;chunk_token<=0;fence<=0;
   tile_at<=0;tile_bytes<=0;am<=0;asyn<=0;ap<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;
   tap_seen<=0;read_pending<=0;tap_fault<=0;written<=0;mask<=0;view_at<=0;final_send<=0;scroll_length<=0;meta_at<=0;map_received313<=0;run_left<=0;run_zero<=0;meta_display<=0;
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
   if(read_n)tap_seen<=0;
   if(capture)begin tap_seen<=1;if(!read359[33])tap_fault<=1;else read_pending<=1;end
   if(read_end&&ap>=24'h400800&&ap<24'h401800&&!invalidate_banks)begin
    if(!read_pending||state!=WAITREAD||ap!=24'h400800+read_count||read_count>=chunk_length)failed<=1;
    read_pending<=0;read_count<=read_count+1'b1;tap_position<=tap_position+((region==2&&stride32&&tap_position[0])?16'd63:16'd1);
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
   if(!fault)case(state)
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
    RCHECK:begin
     if(bad_record||allocation==32'hffffffff||payload_cursor>qlen)failed<=1;
     else begin
      offset<=0;fragment_at<=0;first_fragment<=1;last_fragment<=1;produced<=0;seed<=0;tile_bytes<=0;
      source_total<=zero_tail?16'd2:decoded;chunk_length<=reference?12'd0:zero_tail?12'd2:decoded[11:0];
      tap_position<=region<2?(canonical<<(region==1?5:4)):region==2?(canonical<<1):canonical;
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
        tap_position<=region==2?(canonical<<1)+(stride32?(offset<<5):offset):canonical+offset;
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
     else begin chunk_token<=allocation;read_count<=0;mask<=0;at<=0;
      if(reference)begin if(records_left==1)qretire<=1;state<=EXPOSE;end
      else if(mode==0)state<=TILECHECK;else state<=GET;
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
    TILECHECK:if(word_valid&&!word_end)begin
     if(word_generation!=identity[47:32]||word_kind!=(region==1)||word_slot!=canonical+(tile_bytes>>(region==1?5:4))||word_length!=(region==1?32:16)||tile_bytes+word_length>chunk_length)failed<=1;
     else begin tile_at<=0;state<=TILEREAD;end
    end
    TILEREAD:state<=TILEPUT;
    TILEPUT:if(put_ready)begin
     if(tile_at==word_length-1)begin tile_bytes<=tile_bytes+word_length;state<=tile_bytes+word_length==chunk_length?SEAL:TILECHECK;end
     else begin tile_at<=tile_at+1'b1;state<=TILEREAD;end
    end
    SEAL:begin if(op==8'h92||records_left==1)qretire<=1;state<=EXPOSE;end
    EXPOSE:if(reference||chunk_ready)state<=WAITREAD;
    WAITREAD:;
    TAKE:begin
     read_count<=0;
     if(op==8'h92)begin
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
endmodule
