
// SPDX-License-Identifier: MIT
module nes_core257(output wire capture_materialized366,input wire plan_zero319,plan_step319,output wire [9:0] plan_cursor319,output wire record_last319,output wire [2:0] source_raw278,
 input wire [7:0] ram_a_q,ram_b_q,output wire [9:0] ram_a_addr,ram_b_addr,output wire ram_a_we,ram_b_we,output wire [7:0] ram_a_w,ram_b_w,

 input wire display_write,display_request,output wire display_request_ready,
 output wire display_response_valid,input wire display_response_ready,output wire [7:0] display_response,
 input wire v_begin_valid,v_target_bank,input wire [2:0] v_raw_count,
 input wire v_range_valid,v_map_range,input wire [11:0] v_first,v_count,
 input wire v_check_valid,input wire [7:0] v_check_value,
 input wire v_finish_valid,v_all_consumed,v_display_ack,
 output wire v_ready,output wire v_sealed,
 input wire h_start,input wire [1:0] h_kind,input wire [3:0] h_index,
 input wire h_valid,input wire [7:0] h_data,output wire h_ready,
 input wire context_valid,input wire [7:0] context_data,output wire context_ready,
 input wire transport_crc_pending,transport_empty,input wire [15:0] transport_crc,
 input wire [7:0] transport_byte,output wire [15:0] crc_result,
 output wire output_phase,


 input wire stream_valid,input wire [7:0] stream_data,output wire stream_ready,
 output wire sink_valid,input wire sink_ready,output wire [7:0] sink_data,
 output wire [1:0] sink_kind,output wire [11:0] sink_unit,output wire [4:0] sink_lane,


 input wire display_lease,input wire [15:0] display_generation,input wire [31:0] display_epoch,
 input wire range_external,range_dma_done,
 input wire clk,reset,abort_source,start,output wire start_ready,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [31:0] content_epoch,frame_serial,input wire [2:0] patch_count,

 input wire [7:0] row_count,object_count,exception_count,input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,
 output wire in_valid,in_ready,output wire [7:0] in_data,output wire [12:0] in_offset,
 output wire raw_query,output wire [12:0] raw_index,input wire raw_response,raw_hit,input wire [63:0] raw_data,
 output wire record_valid,input wire record_ready,output reg [7:0] record_length,output reg record_flush,
 output wire byte_valid,input wire byte_ready,output wire [7:0] byte_data,
 input wire ack_valid,output wire ack_ready,input wire ack_accept,input wire [15:0] ack_generation,
 output reg done,output reg [3:0] fault
);
 typedef enum logic[5:0] {IDLE,HEADER,FETCH,FSTORE,BLOCKEND,REQUEST,SREAD,SBYTE,
  GEOTRAILER,RAWSTART,ENDTRAILER,WAITACK,V_STREAM,V_CLEARALL,V_IDLE,V_CLEARFRAME,V_ACTIVE,V_RREAD,V_RWRITE,V_CHECKREAD,V_CHECKTEST,V_WAITDISPLAY,V_RAWINVALID,H_BYTES,H_WRITELO,H_WRITEHI,H_SCROLL,H_HASHREAD,H_HASHBYTE,H_CERT,H_CERTREAD,H_LENLOREAD,H_LENLO,H_LENHIREAD,H_LENHI,D_READ,D_CHECK,D_FETCH,D_RETURN} state_t;
 typedef enum logic[2:0] {H,MASK,SHIFT,GEO,ENDREC} kind_t;
 reg seal_state;
 state_t state;kind_t kind;
reg v_bank,v_mapmode;reg [2:0] v_raw;
 reg [9:0] v_addr;reg [7:0] v_wdata,v_mask,v_value;wire [7:0] v_q=ram_a_q;
 reg [11:0] v_bit_at,v_left,v_map_end;reg [3:0] v_take;reg [1:0] v_initialized;
 reg v_we;


 reg [12:0] cursor,raw_limit;
 assign plan_cursor319=10'd0;
 reg raw_cold;
 reg [3:0] mask_bytes;reg [7:0] mask_acc,new_byte,old1,old2,new1,new2,edge0,edge1;

 reg [2:0] admitted_raw;
 reg [3:0] hash_index,hash_lane;
 reg [10:0] h_count;reg context_complete,display_less;
 reg [15:0] digest;
 reg certificate_ok,digest_ready,scroll_seen;
 reg external_range;
 wire live,lease_ok;
 (* ramstyle="M9K" *) reg [7:0] base_lo[0:4095],base_hi[0:1023];
 reg [7:0] lo_q,hi_q;wire [7:0] a_q=ram_a_q,b_q=ram_b_q;reg bank_q;
 wire [12:0] base_addr=cursor;wire [7:0] base_q=bank_q?hi_q:lo_q;
 wire base_we=live&&state==FSTORE;wire [7:0] base_w=new_byte;
 reg [8:0] a_addr,b_addr;reg a_we,b_we;reg [7:0] a_w,b_w;
 always @(posedge clk)begin
  bank_q<=base_addr[12];lo_q<=base_lo[base_addr[11:0]];
  if(base_we&&!base_addr[12])base_lo[base_addr[11:0]]<=base_w;
 end
 always @(posedge clk)begin hi_q<=base_hi[base_addr[9:0]];if(base_we&&base_addr[12])base_hi[base_addr[9:0]]<=base_w;end
 reg base_valid,cold,raw_mode,left_row,right_row,shift_left;
 reg [31:0] epoch,base_serial;wire [31:0] serial=base_serial+32'd1;
 reg [15:0] generation,checksum,spans,expanded;
 reg [6:0] block_id,row_i,row_size,diff_count;
 reg [7:0] rec_i,build_i;
 reg [10:0] q_maps;reg [7:0] q_objects,q_exceptions;reg [6:0] q_palettes;
 reg [7:0] q_mode;reg q_normal;reg [2:0] q_raw_seen;reg [63:0] q_held;

 reg [2:0] q_section;
 reg q_have,q_pending;
 wire [12:0] q_cursor=state==FSTORE?cursor+13'd1:cursor;
 wire q_want=live&&!output_phase&&state!=IDLE&&((!raw_mode&&q_cursor<4385&&q_cursor!=4320)||(raw_mode&&q_cursor<4398+raw_limit))&&!q_have&&!q_pending;
 wire q_synthetic=!raw_mode&&(cursor==4320||cursor>=4385);
 wire q_last=q_section==2?cursor[2:0]==7:q_section==3?cursor[1:0]==3:
             (q_section==0||q_section==4)?cursor[0]:1'b1;
 reg [10:0] q_index;reg q_first,q_active;
 reg [7:0] q_value;reg [15:0] q_tail;wire [12:0] q_rel=cursor-13'd4385;
 always @*begin
  q_section=0;q_index=0;q_first=1;q_active=0;q_value=q_held[7:0];q_tail=0;
  if(raw_mode)begin q_section=7;q_index=q_cursor-13'd4398;q_active=1;end
  else if(q_cursor<2112)begin q_section=0;q_index=q_cursor[11:1];q_first=!q_cursor[0];q_active=q_index<q_maps;end
  else if(q_cursor<2336)begin q_section=1;q_index=q_cursor-2112;q_active=1;end
  else if(q_cursor<3360)begin q_section=2;q_index=(q_cursor-2336)>>3;q_first=q_cursor[2:0]==0;q_active=q_index<q_objects;end
  else if(q_cursor<3872)begin q_section=3;q_index=(q_cursor-3360)>>2;q_first=q_cursor[1:0]==0;q_active=q_index<q_exceptions;end
  else if(q_cursor<4320)begin q_section=4;q_index=(q_cursor-3872)>>1;q_first=!q_cursor[0];q_active=1;end
  else if(q_cursor==4320)begin q_value=q_mode;q_first=0;end
  else if(q_cursor<4385)begin q_section=5;q_index=q_cursor-4321;q_active=q_index<q_palettes;end
  else begin
   q_first=0;
   case(q_rel[3:1])
    0:q_tail={5'd0,q_maps};1,4:q_tail=224;
    2:q_tail={8'd0,q_objects};3:q_tail={8'd0,q_exceptions};5:q_tail={9'd0,q_palettes};default:q_tail=0;
   endcase
   q_value=q_rel==12?{5'd0,admitted_raw}:q_rel[0]?q_tail[15:8]:q_tail[7:0];
  end
 end
 assign query=raw_query||(q_want&&q_active);
 assign query_kind=raw_query?3'd7:q_section;assign query_index=raw_query?raw_index:{2'd0,q_index};
 assign query_generation=generation;
 assign in_valid=live&&state==FETCH&&(q_have||q_synthetic);
 assign in_offset=cursor;assign in_data=q_value;


 assign output_phase=1'b0;
 assign source_raw278=admitted_raw;
 assign capture_materialized366=live&&!q_pending&&
   (state==BLOCKEND&&cursor==4398+raw_limit);
 reg mask_pending278;reg [8:0] mask_address278;reg [7:0] mask_value278;
 always @(posedge clk)begin
  if(reset||abort_source||fault)begin mask_pending278<=0;mask_address278<=0;mask_value278<=0;end
  else begin
   mask_pending278<=b_we;
   if(b_we)begin mask_address278<=b_addr;mask_value278<=b_w;end
  end
 end
 assign ram_a_addr={1'b1,mask_pending278?mask_address278:a_addr};
 assign ram_a_we=live&&(mask_pending278||a_we);
 assign ram_a_w=mask_pending278?mask_value278:a_w;
 assign ram_b_addr=0;assign ram_b_we=0;assign ram_b_w=0;
 assign v_ready=0;assign v_sealed=0;assign h_ready=0;assign context_ready=0;
 assign display_request_ready=0;assign display_response_valid=0;assign display_response=0;
 assign stream_ready=0;assign sink_valid=0;assign sink_data=0;
 assign sink_kind=0;assign sink_unit=0;assign sink_lane=0;
 wire changed=(raw_mode?raw_cold:cold)||base_q!=new_byte;
 wire [7:0] mask_next=mask_acc|(changed?(8'b1<<row_i[2:0]):8'd0);
 wire shift_ok=!cold&&block_id<32&&(left_row||right_row);
 assign lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;

 assign live=!reset&&!abort_source&&!fault&&lease_ok&&!output_phase;
 assign start_ready=!reset&&!abort_source&&!fault&&state==IDLE;
 assign in_ready=in_valid;assign raw_query=1'b0;assign raw_index=0;
 assign record_valid=live&&state==REQUEST;assign byte_valid=live&&state==SBYTE;assign ack_ready=live&&state==WAITACK&&transport_empty;
 function automatic [15:0] crc16(input [15:0] previous,input [7:0] v);
  reg [15:0] c;integer i;begin c=previous^{v,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction

 wire crc_output=1'b0;
 wire [15:0] crc_previous=crc_output?checksum:transport_crc_pending?transport_crc:checksum;
 wire [7:0] crc_byte=transport_crc_pending?transport_byte:byte_data;
 assign crc_result=crc16(crc_previous,crc_byte);

 reg [7:0] header_byte,out_byte;
 always @*begin
  case(build_i)
   0:header_byte="N";1:header_byte="5";2:header_byte=2;3:header_byte={6'd0,raw_cold,cold};
   4:header_byte=epoch[7:0];5:header_byte=epoch[15:8];6:header_byte=epoch[23:16];7:header_byte=epoch[31:24];
   8:header_byte=base_serial[7:0];9:header_byte=base_serial[15:8];10:header_byte=base_serial[23:16];11:header_byte=base_serial[31:24];
   12:header_byte=serial[7:0];13:header_byte=serial[15:8];14:header_byte=serial[23:16];15:header_byte=serial[31:24];
   16:header_byte=generation[7:0];17:header_byte=generation[15:8];default:header_byte=0;
  endcase
 end
 always @*begin
  a_addr=9'd256+rec_i;b_addr=0;a_we=0;b_we=0;a_w=0;b_w=0;
  if(kind==MASK)a_addr=rec_i<=mask_bytes?9'd383+rec_i:{1'b0,rec_i}-9'd1-{5'd0,mask_bytes};
  case(state)
   HEADER:begin a_addr=9'd256+build_i;a_we=1;a_w=header_byte;end
   FSTORE:begin
    a_addr={2'd0,diff_count};a_we=changed;a_w=new_byte;
    b_addr=9'd384+{5'd0,row_i[6:3]};b_we=row_i[2:0]==7||row_i+1==row_size;b_w=mask_next;
   end
   GEOTRAILER,ENDTRAILER:begin
    a_addr=9'd256+build_i;a_we=1;
    case(build_i)
     0,1:a_w=255;2:a_w=0;3:a_w=state==GEOTRAILER?3:4;
     4:a_w=spans[7:0];5:a_w=spans[15:8];6:a_w=expanded[7:0];7:a_w=expanded[15:8];default:a_w=0;
    endcase
   end
   default:begin end
  endcase
  if(!live)begin a_we=0;b_we=0;end
 end
 always @*begin
  out_byte=a_q;
  if(kind==MASK&&rec_i==0)out_byte={1'b0,block_id};
  if(kind==SHIFT)case(rec_i)
   0:out_byte={1'b1,block_id};1:out_byte=shift_left?1:255;
   2:out_byte=shift_left?new2:edge0;default:out_byte=shift_left?new1:edge1;
  endcase
  if(kind==GEO||kind==ENDREC)begin
   if(rec_i==record_length-2)out_byte=checksum[7:0];
   if(rec_i==record_length-1)out_byte=checksum[15:8];
  end
 end
 assign byte_data=out_byte;
 assign record_last319=rec_i+8'd1==record_length;
 task automatic emit_record(input kind_t k,input [7:0] n);
  begin kind<=k;record_length<=n;record_flush<=k==ENDREC;rec_i<=0;state<=REQUEST;end
 endtask
 task automatic next_block;
  begin
   if(raw_mode&&cursor==4398+raw_limit)begin build_i<=0;state<=ENDTRAILER;end
   else if(!raw_mode&&cursor==4398)begin build_i<=0;state<=GEOTRAILER;end
   else begin
    block_id<=block_id+1'b1;row_i<=0;diff_count<=0;mask_acc<=0;left_row<=1;right_row<=1;
    row_size<=cursor<2112?66:cursor==4352?46:64;mask_bytes<=cursor<2112?9:cursor==4352?6:8;state<=FETCH;
   end
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;external_range<=0;v_bank<=0;v_raw<=0;v_mapmode<=0;v_bit_at<=0;v_left<=0;v_map_end<=0;v_take<=0;v_mask<=0;v_value<=0;v_initialized<=0;seal_state<=0;admitted_raw<=0;hash_index<=0;hash_lane<=0;h_count<=0;context_complete<=0;display_less<=0;q_maps<=0;q_objects<=0;q_exceptions<=0;q_palettes<=0;q_mode<=0;q_normal<=0;q_raw_seen<=0;q_held<=0;q_have<=0;q_pending<=0;digest<=0;certificate_ok<=0;digest_ready<=0;scroll_seen<=0;kind<=H;done<=0;fault<=0;base_valid<=0;cold<=1;raw_cold<=1;raw_mode<=0;
   epoch<=0;base_serial<=0;generation<=0;checksum<=16'hffff;spans<=0;expanded<=0;
   cursor<=0;raw_limit<=0;block_id<=0;row_i<=0;row_size<=66;diff_count<=0;mask_bytes<=9;
   mask_acc<=0;new_byte<=0;old1<=0;old2<=0;new1<=0;new2<=0;edge0<=0;edge1<=0;
   left_row<=1;right_row<=1;shift_left<=0;rec_i<=0;build_i<=0;record_length<=0;record_flush<=0;
  end else begin
   done<=0;
   if(abort_source)begin if(!fault)fault<=4;base_valid<=0;seal_state<=0;end
   else if(state!=IDLE&&state!=V_CLEARALL&&!lease_ok)begin fault<=2;base_valid<=0;end
   else if(!fault&&ack_valid&&!output_phase&&state!=WAITACK&&state!=IDLE)begin fault<=5;base_valid<=0;end

   else if(!fault)begin
    if(q_want)begin if(q_active)q_pending<=1;else begin q_held<=0;q_have<=1;end end
    if(q_pending&&raw_response)begin
     q_pending<=0;
     if(!raw_hit||(q_section==0&&raw_data[63:15]!=0)||(q_section==1&&raw_data[63:8]!=0)||
        (q_section==3&&raw_data[63:32]!=0)||((q_section==5||q_section==7)&&raw_data[63:6]!=0))fault<=3;
     else if(q_section==4)begin
      if(raw_data[49])begin
       if(raw_data[63:53]!=0||raw_data[48:0]!=0||raw_data[52:50]!=q_raw_seen||q_raw_seen>=admitted_raw)fault<=3;
       else begin q_held<={50'd0,raw_data[52:50],1'b1,10'd0};q_raw_seen<=q_raw_seen+1'b1;q_have<=1;end
      end else if(raw_data[63:49]!=0||(raw_data[43:36]!=8'h18&&raw_data[43:36]!=8'h1e)||
                  (q_normal&&raw_data[43:36]!=q_mode)||raw_data[48:44]>=(q_palettes==32?2'd1:2'd2))fault<=3;
      else begin q_held<={54'd0,raw_data[44],raw_data[32:30],raw_data[10],raw_data[4:0]};q_normal<=1;q_mode<=raw_data[43:36];q_have<=1;end
     end else begin q_held<=raw_data;q_have<=1;end
    end

    case(state)
    IDLE:if(start)begin
     if(patch_count>2||row_count!=224||!group_count||group_count>32||object_count>128||exception_count>128||!palette_count||palette_count>2||!frame_owned||!geometry_valid||content_epoch==0||frame_serial==0||frame_serial==32'hffffffff||
        (!base_valid&&frame_serial!=1)||(base_valid&&(content_epoch!=epoch||frame_serial!=serial)))begin fault<=1;base_valid<=0;end
     else begin
      q_maps<={group_count,5'd0}+group_count;q_objects<=object_count;q_exceptions<=exception_count;q_palettes<=palette_count==1?32:64;q_mode<=0;q_normal<=0;q_raw_seen<=0;q_have<=0;q_pending<=0;admitted_raw<=patch_count;epoch<=content_epoch;generation<=frame_generation;cold<=!base_valid;raw_cold<=!base_valid||patch_count!=admitted_raw;raw_limit<={2'd0,patch_count,8'd0};
      cursor<=0;block_id<=0;row_i<=0;row_size<=66;mask_bytes<=9;diff_count<=0;mask_acc<=0;left_row<=1;right_row<=1;
      checksum<=16'hffff;spans<=0;expanded<=0;build_i<=0;raw_mode<=0;state<=HEADER;
     end
    end
    HEADER:if(build_i==19)emit_record(H,20);else build_i<=build_i+1'b1;

    FETCH:if(in_valid)begin
     if(cursor>=4398+raw_limit||(!raw_mode&&cursor>=4398)||(!raw_mode&&cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))begin fault<=3;base_valid<=0;end
     else begin new_byte<=q_value;state<=FSTORE;end
     if(!q_synthetic)begin q_held<={8'd0,q_held[63:8]};if(q_last)q_have<=0;end
    end
    FSTORE:begin
     cursor<=cursor+1'b1;if(changed)diff_count<=diff_count+1'b1;
     mask_acc<=row_i[2:0]==7?8'd0:mask_next;
     if(row_i==0)edge0<=new_byte;if(row_i==1)edge1<=new_byte;
     if(row_i>=2)begin if(base_q!=new2)left_row<=0;if(new_byte!=old2)right_row<=0;end
     old2<=old1;old1<=base_q;new2<=new1;new1<=new_byte;
     if(row_i+1==row_size)state<=BLOCKEND;else begin row_i<=row_i+1'b1;state<=FETCH;end
    end
    BLOCKEND:if(!diff_count)next_block();else begin
     if(!raw_mode)begin spans<=spans+1'b1;expanded<=expanded+(shift_ok?16'd66:{9'd0,diff_count});end
     if(shift_ok)begin shift_left<=left_row;emit_record(SHIFT,4);end
     else emit_record(MASK,{1'b0,diff_count}+{4'd0,mask_bytes}+8'd1);
    end
    REQUEST:if(record_ready)state<=SREAD;
    SREAD:state<=SBYTE;
    SBYTE:if(byte_ready)begin
     if((kind!=GEO&&kind!=ENDREC)||rec_i<record_length-2)checksum<=crc_result;
     if(rec_i+1==record_length)case(kind)
      H:state<=FETCH;MASK,SHIFT:next_block();GEO:state<=RAWSTART;
      ENDREC:state<=WAITACK;default:begin fault<=6;base_valid<=0;end
     endcase
     else begin rec_i<=rec_i+1'b1;state<=SREAD;end
    end
    GEOTRAILER:if(build_i==7)emit_record(GEO,10);else build_i<=build_i+1'b1;
    RAWSTART:begin
     raw_mode<=1;cursor<=4398;block_id<=68;row_i<=0;row_size<=64;mask_bytes<=8;
     diff_count<=0;mask_acc<=0;q_have<=0;q_pending<=0;
     if(!raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=FETCH;
    end
    ENDTRAILER:if(build_i==3)emit_record(ENDREC,6);else build_i<=build_i+1'b1;
    WAITACK:if(ack_valid&&ack_ready)begin
     if(!ack_accept||ack_generation!=generation)begin fault<=5;base_valid<=0;end
     else begin base_valid<=1;base_serial<=serial;done<=1;rec_i<=0;context_complete<=0;display_less<=0;cursor<=0;state<=IDLE;end
    end
    default:begin fault<=6;base_valid<=0;end
   endcase
   end
  end
 end

endmodule
