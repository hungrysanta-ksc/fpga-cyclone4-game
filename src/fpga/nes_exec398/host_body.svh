// SPDX-License-Identifier: MIT
// The host protocol is bytecode. This layer owns only physical IO handshakes,
// the immutable lease, and exact bus/token/CRC events.
 wire rst=reset||cancel;
 @IO_CONSTANTS@
 wire[83:0] admitted286;wire[48:0] identity=admitted286[48:0];wire iv,ar;
 reg have_identity,new_frame,nes_admitted,failed,invalidate_banks;
 reg[2:0] phase;reg[31:0] allocation,last_serial,chunk_token,fence;
 wire can_admit=init278&&(!have_identity||phase==5);
 nes_native_mailbox206 #(.WIDTH(84)) admission(.src_clk(nes_clk),.dst_clk(host_clk),.reset(rst),
  .src_valid(identity_valid&&!nes_admitted),.src_ready(ar),.src_data({epoch278,raw278,bank,generation,serial}),
  .dst_valid(iv),.dst_ready(can_admit),.dst_data(admitted286));
 assign identity_ready=ar&&!nes_admitted&&!rst;
 assign grant278=iv&&can_admit&&!rst;assign grant_epoch278=admitted286[83:52];assign grant_raw278=admitted286[51:49];
 assign grant_serial278=identity[31:0];assign grant_generation278=identity[47:32];assign next_token=allocation;
 always @(posedge nes_clk or posedge rst)if(rst)nes_admitted<=0;else if(identity_valid&&identity_ready)nes_admitted<=1;else if(display_ack)nes_admitted<=0;
 wire mv,mw,mready,iov,iow,ioready,cpufault,handler;wire[7:0] ma,md,mq,ioa,iod,ioq;wire[11:0] code_addr,debug_pc;
 reg[17:0] program398[0:4095],code_q;reg[11:0] code_tag;
 initial $readmemh("program398.hex",program398);
 always @(posedge host_clk)begin code_q<=program398[code_addr];code_tag<=code_addr;end
 wire queue_irq398;wire[7:0]queue_q398;
 nes_byte398 #(.ENTRY(@ENTRY@),.IRQ_ENTRY(@IRQ@)) control(.clk(host_clk),.reset(rst),.stop(fault),.irq(footer_request396||queue_irq398),
  .code_address(code_addr),.code_data(code_q),.code_ready(code_tag==debug_pc),
  .mem_valid(mv),.mem_write(mw),.mem_address(ma),.mem_data(md),.mem_ready(mready),.mem_q(mq),
  .io_valid(iov),.io_write(iow),.io_address(ioa),.io_data(iod),.io_ready(ioready),.io_q(ioq),.fault(cpufault),.in_irq(handler),.debug_pc(debug_pc));
 wire io_fire=iov&&ioready&&!fault&&!rst;wire out398=io_fire&&iow;
 reg[2:0] footer_at398;assign footer_index396=footer_at398;assign footer_address396=250+footer_at398;
 assign footer_capture396=out398&&ioa==IO_FOOTER_CAPTURE&&footer_request396;
 wire footer_active396=footer_request396;
 reg[7:0] parser_address;reg qretire,consume_record312,canonical_write;
 reg[8:0] canonical_address;reg[7:0] held;
 wire qr,qfault,storage_empty312;wire[8:0] queue_length312;wire[7:0] qdata;
 reg[15:0] canonical,fragment_at,tap_position;reg[11:0] chunk_length,read_count;
 reg[7:0] attributes;reg[2:0] region;reg active_fragment,begun,finish_pending,tiles_closed;
 reg[10:0] scroll_length;wire reference=attributes[4],stride32=attributes[5],zero_tail=attributes[6];reg first_fragment,last_fragment;
 wire[127:0] progress_status={5'd0,1'b0,staged,tiles_closed,(staged?chunk_token[7:0]:allocation[7:0]),(staged?chunk_token[15:8]:allocation[15:8]),
  (staged?chunk_token[23:16]:allocation[23:16]),(staged?chunk_token[31:24]:allocation[31:24]),{7'd0,out398,ioa,iod,8'd0},
  chunk_length[7:0],4'd0,chunk_length[11:8],5'd0,identity[48],1'b0,region==1,canonical[7:0],canonical[15:8],identity[39:32],identity[47:40]};
 nes_queue260 queue(.irq398(queue_irq398),.control_write398(out398),.control_address398(ioa),.control_q398(queue_q398),.admit319(queue_admit319),.expected_select313(canonical_write||finish_pending),
  .expected_write313(canonical_write),.expected_address313(finish_pending?expected_addr332:canonical_address),.expected_data313(held),
  .frame_start312(grant278),.frame_serial312(identity[31:0]),.frame_generation312(identity[47:32]),.record312(192'd0),.load_enable312(1'b0),.load_at315(4'd0),
  .storage_empty312(storage_empty312),.record_valid312(),.record_at312(),.record_byte312(),.link270(link270),.status270(status270),.crc_take270(crc_take270),
  .progress_status(progress_status),.clk(host_clk),.reset(rst),.enable(1'b1),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .selected(selected),.miso(miso),.sn_address(parser_address),.sn_data(qdata),.packet_ready(qr),.packet_length(queue_length312),.parser_retire(qretire),.consume_record312(consume_record312),.fault(qfault));
 assign expected_data332=qdata;
 wire begin_ready,put_ready,chunk_ready,pe,ce,aoe,tile_empty396;wire[7:0] aperture_data,tile_q;wire tile_fault;
 wire word_valid,word_ready,word_end,word_partial,word_kind;wire[15:0]word_generation;wire[9:0]word_slot;wire[5:0]word_length;
 wire[9:0]stage_addr;wire stage_write;wire[7:0]stage_data;wire ctx_pause,stage_atomic;
 wire[9:0]metadata_addr;wire metadata_write;wire[7:0]metadata_data;
 wire open398=iov&&iow&&ioa==IO_OPEN&&!fault&&!rst;
 wire put398=iov&&iow&&ioa==IO_PUT&&!fault&&!rst;
 wire seal398=out398&&ioa==IO_SEAL;
 wire consume398=out398&&ioa==IO_TAKE&&!reference;
 nes_tile_link394 tile_link(.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.source_fault(fault),
  .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
  .end_valid(end_valid),.end_partial(end_partial295),.end_ready(end_ready),.end_generation(end_generation),
  .word_valid(word_valid),.word_ready(word_ready),.word_end(word_end),.word_partial(word_partial),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),
  .read_at(metadata_addr),.meta_write(metadata_write),.meta_data(metadata_data),.read_data(tile_q),.fault(tile_fault));
 nes_stage396 aperture(.clk(host_clk),.reset(rst),.active(!fault&&have_identity),.meta_pause398(ctx_pause),.meta_atomic398(stage_atomic),
  .begin_valid(open398&&!reference),.begin_tile(region<2),.begin_length(chunk_length),.begin_token(allocation),.generation(identity[47:32]),.kind(region==1),.first(canonical[9:0]),
  .begin_ready(begin_ready),.byte_valid(put398),.byte_data(iod),.byte_ready(put_ready),.seal(seal398),.producer_error(pe),.chunk_ready(chunk_ready),
  .consume(consume398),.consume_token(chunk_token),.consume_error(ce),.tile_empty(tile_empty396),
  .word_valid(word_valid),.word_end(word_end),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),.word_ready(word_ready),
  .meta_address(stage_addr),.meta_write(stage_write),.meta_data(stage_data),.meta_q(tile_q),.address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe));
 assign tile_closed267=tiles_closed;
 // One physical metadata port. CORE/HEADER can steal only a resumable stage
 // read,never a pending payload copy,stamp write or binding capture.
 reg ctx_busy,ctx_done;reg[7:0]ctx_q;reg[1:0]return_owner;
 reg header_seen,header_done;reg[23:0]header_address;reg[31:0]header_token;reg[7:0]header_q;
 wire header_select=address>=24'h006080&&address<24'h00608c;
 wire header_request=header_select&&!read_n&&write_n&&!header_seen&&phase==1;
 wire header_grant=header_request&&!stage_atomic&&!fault&&!rst;
 wire core_grant=mv&&ma<224&&!ctx_busy&&!header_request&&!stage_atomic&&!fault&&!rst;
 assign ctx_pause=header_grant||core_grant;
 assign metadata_addr=header_grant?10'd800+address[3:0]:core_grant?10'd800+ma:stage_addr;
 assign metadata_write=!rst&&!fault&&(core_grant?mw:!header_grant&&stage_write);
 assign metadata_data=core_grant?md:stage_data;
 assign mq=ctx_q;assign mready=ctx_done;
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin ctx_busy<=0;ctx_done<=0;return_owner<=0;ctx_q<=0;header_seen<=0;header_done<=0;header_address<=0;header_token<=0;header_q<=0;end
  else begin
   if(return_owner==1)begin ctx_q<=tile_q;ctx_done<=1;end
   if(return_owner==2)begin header_q<=tile_q;header_done<=1;end
   return_owner<=0;
   if(core_grant)begin ctx_busy<=1;return_owner<=1;end
   if(mv&&mready)begin ctx_done<=0;ctx_busy<=0;end
   if(read_n||header_address!=address)begin header_seen<=0;header_done<=0;end
   if(header_grant)begin header_seen<=1;header_address<=address;header_token<=chunk_token;return_owner<=2;end
  end
 end
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg[23:0]am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg[7:0]dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg wm,ws,rm,rs;
 reg[23:0]ap;reg[7:0]dp;reg wp,rp,tap_seen,read_pending,tap_fault,taken;
 reg[31:0]written;reg[3:0]mask,view_at;reg view_advanced,display_wait,display_pending;reg[7:0]view_byte;
 wire write_end=ws&&!wp&&rp,read_end=rs&&!rp;
 wire capture=phase==1&&!reference&&chunk_ready&&!tap_seen&&!read_n&&write_n&&address>=24'h400800&&address<24'h401800&&bus_valid&&!invalidate_banks;
 wire crc_byte=region==5&&!zero_tail&&(tap_position<scroll_length||(grant_raw278!=0&&tap_position>=3169));
 wire crc_start=tap_position==0||(tap_position>=3169&&(tap_position-3169)%16==0);
 assign read359={capture&&ready359&&!read_pending&&address==24'h400800+read_count&&read_count<chunk_length&&!fault&&!rst,
  crc_byte,crc_start,region==2?4'd14:region<2?4'd7:4'd2,region,tap_position,aperture_data};
 wire good_consume=phase==1&&read_count==chunk_length&&ready359&&!read_pending&&mask==15&&written==chunk_token&&dp==8'ha5;
 assign fault=failed||qfault||tile_fault||tap_fault||cpufault||pe||ce;
 assign staged=phase==1&&!fault&&!rst;assign ordinary_ready=staged;assign receipt_committed=begun&&!fault&&!rst;
 assign jobs_committed336=!staged&&ready359&&!read_pending&&!active_fragment&&tile_empty396&&!rst&&!fault;
 assign crc_reset287=out398&&ioa==IO_CRC_RESET;
 assign context_valid=iov&&iow&&ioa==IO_CTX&&!fault&&!rst;assign context_data=iod;
 assign begin_valid=iov&&iow&&ioa==IO_BEGIN&&!fault&&!rst;assign begin_bank=identity[48];assign begin_raw=grant_raw278;
 assign ordinary_finish=finish_pending&&range_ready&&!sealed&&!fault&&!rst;
 assign display_request=iov&&iow&&ioa==IO_DISPLAY_REQ&&!fault&&!rst;
 assign display_response_ready=display_wait&&!fault&&!rst;
 assign display_write=0;assign range_valid=0;assign range_first=0;assign range_count=1;assign range_dma_done=0;
 assign ordinary_range=0;assign ordinary_first=0;assign ordinary_end300=1;assign ordinary_stream=0;assign ordinary_byte=0;assign ordinary_check=0;
 assign ordinary_hash_start=0;assign ordinary_hash_kind=0;assign ordinary_hash_index=0;assign ordinary_hash_byte=0;
 assign exec_start298=0;assign exec_kind298=0;assign exec_op298=0;assign exec_length298=0;assign exec_data298=0;
 assign ctx_address375=0;assign ctx_write375=0;assign ctx_data375=0;
 reg final_send,final_seen;wire fr,fv;
 nes_native_mailbox206 #(.WIDTH(1)) final_ack(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),.src_valid(final_send),.src_ready(fr),.src_data(1'b1),.dst_valid(fv),.dst_ready(1'b1),.dst_data());
 assign host_ack278=final_send&&fr&&!rst;assign display_ack=fv&&!rst;assign retired=final_seen&&core_idle&&!rst;
 always @(posedge nes_clk or posedge rst)if(rst)final_seen<=0;else if(identity_valid&&identity_ready)final_seen<=0;else if(display_ack)final_seen<=1;
 reg[7:0]control_byte,io_read;reg io_ready;
 wire[31:0]previous_serial=identity[31:0]-1'b1;
 always @*begin
  io_read=0;io_ready=1;
  if(ioa>=16&&ioa<28)case(ioa-16)
   0,1,2,3:io_read=grant_epoch278>>(8*(ioa-16));4,5,6,7:io_read=identity[31:0]>>(8*(ioa-20));
   8:io_read=identity[39:32];9:io_read=identity[47:40];10:io_read={7'd0,identity[48]};11:io_read={5'd0,grant_raw278};default:;
  endcase
  else if(ioa>=96&&ioa<108)case(ioa-96)
   0:io_read=8'h72;1:io_read=8'h24;2:io_read={7'd0,identity[48]};4,5,6,7:io_read=previous_serial>>((ioa-100)*8);8:io_read=1;default:io_read=0;
  endcase
  else if(ioa>=112&&ioa<=126)io_read=queue_q398;
  else if(ioa>=128&&ioa<=175)io_read=link270[153:146];
  else case(ioa)
   IO_NEW_FRAME:io_read=new_frame;IO_QUEUE_READY:io_read=qr&&have_identity&&!qretire;
   IO_QL_LO:io_read=queue_length312[7:0];IO_QL_HI:io_read={7'd0,queue_length312[8]};IO_QDATA:io_read=qdata;
   IO_OPEN:io_ready=reference||begin_ready;IO_PUT:io_ready=put_ready;IO_CTX:io_ready=context_ready;IO_BEGIN:io_ready=range_ready;
   IO_READY:io_read=chunk_ready;IO_TAKEN:io_read=taken;IO_RANGE_READY:io_read=range_ready;IO_SEALED:io_read=sealed;
   IO_TILES_CLOSED:io_read=tiles_closed;IO_DISPLAY_REQ:io_ready=display_request_ready;
   IO_DISPLAY_DATA:begin io_ready=display_pending;io_read=view_byte;end
   IO_VIEW_ADVANCE:begin io_ready=view_advanced;io_read={4'd0,view_at};end
   IO_FINAL_ACK:io_read=phase==5;
   default:;
  endcase
 end
 assign ioready=io_ready;assign ioq=io_read;
 always @*begin
  control_byte=0;
  case(address[7:0])
   0,8'h40:control_byte=staged;1:control_byte={fault||rst,invalidate_banks,6'd0};
   8'h48,8'h49,8'h4a,8'h4b:control_byte=(phase==1?chunk_token:fence)>>(address[1:0]*8);
   8'h51:control_byte=receipt_committed;8'h52:control_byte=sealed;8'h54:control_byte=phase==3;
   8'h8c:control_byte=fragment_at[7:0];8'h8d:control_byte=fragment_at[15:8];8'h8e:control_byte=chunk_length[7:0];8'h8f:control_byte={4'd0,chunk_length[11:8]};
   8'h90:control_byte={6'd0,last_fragment,first_fragment};8'h91,8'h92,8'h93,8'h94:control_byte=identity[31:0]>>((address[2:0]-1)*8);
   8'h95:control_byte=identity[39:32];8'h96:control_byte=identity[47:40];8'h97:control_byte={7'd0,identity[48]};8'h98:control_byte=identity[31:0]<=2;8'h99:control_byte=begun&&phase!=5;
   default:;
  endcase
 end
 wire display_address=address>=24'h006070&&address<24'h00607c;
 assign data_out=header_select?header_q:display_address?held:address[23:8]==16'h0060 ? control_byte:aperture_data;
 assign bus_valid=!read_n&&write_n&&(address==24'h006001||(!rst&&!fault&&!invalidate_banks&&
  ((address[23:8]==16'h0060&&(!display_address||phase==3)&&(!header_select||(header_done&&header_address==address&&header_token==chunk_token)))||(!aoe&&phase==1))));
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin allocation<=INITIAL_TOKEN;last_serial<=0;end
  else if(!rst&&!fault)begin
   if(out398&&ioa==IO_OPEN||out398&&ioa==IO_PHASE&&iod==2)begin if(allocation!=32'hffffffff)allocation<=allocation+1'b1;end
   if(grant278&&identity[31:0]>last_serial)last_serial<=identity[31:0];
  end
 end
 always @(posedge host_clk or posedge rst)begin
  if(rst)begin
   have_identity<=0;new_frame<=0;failed<=0;invalidate_banks<=1;phase<=0;footer_at398<=0;
   parser_address<=0;qretire<=0;consume_record312<=0;canonical_write<=0;canonical_address<=0;held<=0;
   canonical<=0;fragment_at<=0;tap_position<=0;chunk_length<=0;read_count<=0;attributes<=0;region<=0;active_fragment<=0;begun<=0;finish_pending<=0;scroll_length<=0;first_fragment<=0;last_fragment<=0;tiles_closed<=0;
   am<=0;asyn<=0;ap<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;tap_seen<=0;read_pending<=0;tap_fault<=0;taken<=0;
   written<=0;mask<=0;view_at<=0;view_advanced<=0;display_wait<=0;display_pending<=0;view_byte<=0;final_send<=0;chunk_token<=0;fence<=0;
  end else begin
   am<=address;asyn<=am;ap<=asyn;dm<=data_in;ds<=dm;dp<=ds;wm<=write_n;ws<=wm;wp<=ws;rm<=read_n;rs<=rm;rp<=rs;
   qretire<=0;consume_record312<=0;canonical_write<=0;
   if(mv&&ma>=224)failed<=1; // Context may never wrap into tile/stamp storage.
   if(final_send&&fr)final_send<=0;
   if(fault)invalidate_banks<=1;
   if(grant278)begin if(identity[31:0]<=last_serial)failed<=1;else begin have_identity<=1;new_frame<=1;phase<=0;begun<=0;tiles_closed<=0;active_fragment<=0;finish_pending<=0;end end
   if(mv&&mready&&mw&&ma==52)active_fragment<=md[0];
   if(read_n)tap_seen<=0;
   if(capture)begin tap_seen<=1;if(!read359[33])tap_fault<=1;else read_pending<=1;end
   if(read_end&&ap>=24'h400800&&ap<24'h401800&&!invalidate_banks)begin
    if(!read_pending||phase!=1||ap!=24'h400800+read_count||read_count>=chunk_length)failed<=1;
    read_pending<=0;read_count<=read_count+1'b1;tap_position<=tap_position+((region==2&&stride32&&tap_position[0])?16'd63:16'd1);
   end
   if(word_valid&&word_end&&word_ready)begin if(word_generation!=identity[47:32])failed<=1;else if(!word_partial)tiles_closed<=1;end
   if(write_end)begin
    if(ap==24'h00606f&&dp==8'hee)failed<=1;
    if(ap==24'h006006&&dp==8'ha5)invalidate_banks<=0;
    if(!invalidate_banks)begin
     if(ap>=24'h00604c&&ap<=24'h00604f)begin written[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;end
     if(ap==24'h006050)begin mask<=0;if(!good_consume)failed<=1;else begin phase<=0;taken<=1;end end
     if(ap==24'h006058)begin mask<=0;if(phase!=4||!storage_empty312||active_fragment||!tile_empty396||!sealed||view_at!=12||dp!=8'h5a||mask!=15||written!=fence)failed<=1;else begin final_send<=1;phase<=5;end end
    end
   end
   if(read_end&&ap>=24'h006070&&ap<24'h00607c&&!invalidate_banks)begin
    if(phase!=3||ap!=24'h006070+view_at||view_at>=12||!sealed)failed<=1;else begin view_at<=view_at+1'b1;view_advanced<=1;phase<=0;end
   end
   if(display_response_valid&&display_response_ready)begin view_byte<=display_response;display_wait<=0;display_pending<=1;end
   if(io_fire&&!iow)begin if(ioa==IO_VIEW_ADVANCE)view_advanced<=0;if(ioa==IO_DISPLAY_DATA)display_pending<=0;end
   if(out398)case(ioa)
    IO_FAULT:failed<=1;IO_FRAME_INIT:new_frame<=0;IO_QADDR:parser_address<=iod;
    IO_RETIRE:qretire<=1;IO_CONSUME:consume_record312<=1;
    IO_CANON0:canonical[7:0]<=iod;IO_CANON1:canonical[15:8]<=iod;IO_ATTR:attributes<=iod;
    IO_REFERENCE:region<=iod[2:0];IO_TAP0:tap_position[7:0]<=iod;IO_TAP1:tap_position[15:8]<=iod;
    IO_LEN0:chunk_length[7:0]<=iod;IO_LEN1:chunk_length[11:8]<=iod[3:0];IO_OFFSET0:fragment_at[7:0]<=iod;IO_OFFSET1:fragment_at[15:8]<=iod;
    IO_FLAGS:begin first_fragment<=iod[0];last_fragment<=iod[1];end
    IO_OPEN:begin if(allocation==32'hffffffff)failed<=1;else begin chunk_token<=allocation;read_count<=0;mask<=0;taken<=0;end end
    IO_TAKE:begin taken<=0;read_count<=0;end
    IO_PHASE:if(iod==2)begin if(!sealed||!tile_empty396||allocation==32'hffffffff)failed<=1;else begin fence<=allocation;view_at<=0;phase<=0;end end else phase<=iod[2:0];
    IO_BEGIN_FLAG:begun<=iod[0];IO_SCROLL0:scroll_length[7:0]<=iod;IO_SCROLL1:scroll_length[10:8]<=iod[2:0];
    IO_EXPECTED_LO:canonical_address[7:0]<=iod;IO_EXPECTED_HI:canonical_address[8]<=iod[0];IO_EXPECTED_DATA:begin canonical_write<=1;held<=iod;end
    IO_FINISH:finish_pending<=1;IO_DISPLAY_REQ:display_wait<=1;
    IO_DISPLAY_PUBLISH:begin held<=iod;phase<=3;end
    IO_FOOTER_INDEX:footer_at398<=iod[2:0];
    default:;
   endcase
  end
 end
// synthesis translate_off
`ifndef SYNTHESIS
 // Debug-only cold-context views. They do not drive any functional output.
 wire[7:0]op=tile_link.memory[842];wire[95:0]record394={tile_link.memory[811],tile_link.memory[810],tile_link.memory[809],tile_link.memory[808],tile_link.memory[807],tile_link.memory[806],tile_link.memory[805],tile_link.memory[804],tile_link.memory[803],tile_link.memory[802],tile_link.memory[801],tile_link.memory[800]};
 localparam TAKE=16,DONE=31,DVIEW=30,WAITREAD=15,ENDWAIT=27,RCHECK=6;
 wire[5:0]state=taken?TAKE:phase==5?DONE:phase==3?DVIEW:phase==1?WAITREAD:6'd0;
 wire[7:0]at=tile_link.memory[844];wire[8:0]qlen={tile_link.memory[825][0],tile_link.memory[824]};
 wire[15:0]source_total={tile_link.memory[837],tile_link.memory[836]};wire[15:0]produced={tile_link.memory[847],tile_link.memory[846]};
 wire[15:0]destination=record394[15:0],store=record394[31:16],decoded=record394[47:32];
 wire requirements_complete313=tile_link.memory[863][0],prelude_done=tile_link.memory[865][0];
`endif
// synthesis translate_on
endmodule
