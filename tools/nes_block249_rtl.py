# SPDX-License-Identifier: MIT
"""Experimental complete fixed-block encoder; projected input is not bound."""
RTL=r'''
// SPDX-License-Identifier: MIT
module nes_source_block249(
 input wire clk,reset,abort_source,start,output wire start_ready,
 input wire frame_owned,geometry_valid,input wire [15:0] frame_generation,
 input wire [31:0] content_epoch,frame_serial,input wire [2:0] patch_count,
 input wire in_valid,output wire in_ready,input wire [7:0] in_data,input wire [12:0] in_offset,
 output wire raw_query,output wire [12:0] raw_index,input wire raw_response,raw_hit,input wire [63:0] raw_data,
 output wire record_valid,input wire record_ready,output reg [7:0] record_length,output reg record_flush,
 output wire byte_valid,input wire byte_ready,output wire [7:0] byte_data,
 input wire ack_valid,output wire ack_ready,input wire ack_accept,input wire [15:0] ack_generation,
 output reg done,output reg [3:0] fault
);
 typedef enum logic[4:0] {IDLE,HEADER,FETCH,FSTORE,BLOCKEND,REQUEST,SREAD,SBYTE,
  GEOTRAILER,RAWSTART,RAWASK,RAWWAIT,RAWCHECK,ENDTRAILER,WAITACK} state_t;
 typedef enum logic[2:0] {H,MASK,SHIFT,GEO,RAW,ENDREC} kind_t;
 state_t state;kind_t kind;
 reg [12:0] cursor,raw_at,raw_limit;
 reg [3:0] mask_bytes;reg [7:0] mask_acc,new_byte,old1,old2,new1,new2,edge0,edge1;
 wire live;
 (* ramstyle="M9K" *) reg [7:0] base_lo[0:4095],base_hi[0:511],scratch[0:511];
 reg [7:0] lo_q,hi_q,a_q,b_q;reg bank_q;
 wire [12:0] base_addr=cursor;wire [7:0] base_q=bank_q?hi_q:lo_q;
 wire base_we=live&&state==FSTORE;wire [7:0] base_w=new_byte;
 reg [8:0] a_addr,b_addr;reg a_we,b_we;reg [7:0] a_w,b_w;
 always @(posedge clk)begin
  bank_q<=base_addr[12];lo_q<=base_lo[base_addr[11:0]];
  if(base_we&&!base_addr[12])base_lo[base_addr[11:0]]<=base_w;
 end
 always @(posedge clk)begin hi_q<=base_hi[base_addr[8:0]];if(base_we&&base_addr[12])base_hi[base_addr[8:0]]<=base_w;end
 always @(posedge clk)begin a_q<=scratch[a_addr];if(a_we)scratch[a_addr]<=a_w;end
 always @(posedge clk)begin b_q<=scratch[b_addr];if(b_we)scratch[b_addr]<=b_w;end
 reg base_valid,cold,raw_mode,left_row,right_row,shift_left;
 reg [31:0] epoch,base_serial;wire [31:0] serial=base_serial+32'd1;
 reg [15:0] generation,checksum,spans,expanded;
 reg [6:0] block_id,row_i,row_size,diff_count;
 reg [7:0] rec_i,build_i,raw_count;
 wire changed=cold||base_q!=new_byte;
 wire [7:0] mask_next=mask_acc|(changed?(8'b1<<row_i[2:0]):8'd0);
 wire shift_ok=!cold&&block_id<32&&(left_row||right_row);
 wire lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;
 assign live=!reset&&!abort_source&&!fault&&lease_ok;
 assign start_ready=!reset&&!abort_source&&!fault&&state==IDLE;
 assign in_ready=live&&state==FETCH;assign raw_query=live&&state==RAWASK;assign raw_index=cursor;
 assign record_valid=live&&state==REQUEST;assign byte_valid=live&&state==SBYTE;assign ack_ready=live&&state==WAITACK;
 function automatic [15:0] crc16(input [15:0] previous,input [7:0] v);
  reg [15:0] c;integer i;begin c=previous^{v,8'd0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;end
 endfunction
 reg [7:0] header_byte,out_byte;
 always @*begin
  case(build_i)
   0:header_byte="N";1:header_byte="5";2:header_byte=1;3:header_byte={7'd0,cold};
   4:header_byte=epoch[7:0];5:header_byte=epoch[15:8];6:header_byte=epoch[23:16];7:header_byte=epoch[31:24];
   8:header_byte=base_serial[7:0];9:header_byte=base_serial[15:8];10:header_byte=base_serial[23:16];11:header_byte=base_serial[31:24];
   12:header_byte=serial[7:0];13:header_byte=serial[15:8];14:header_byte=serial[23:16];15:header_byte=serial[31:24];
   16:header_byte=generation[7:0];17:header_byte=generation[15:8];default:header_byte=0;
  endcase
 end
 always @*begin
  a_addr=9'd256+rec_i;b_addr=0;a_we=0;b_we=0;a_w=0;b_w=0;
  if(kind==MASK)a_addr=rec_i<=mask_bytes?9'd383+rec_i:{1'b0,rec_i}-9'd1-{5'd0,mask_bytes};
  if(kind==RAW)a_addr={1'b0,rec_i}-9'd3;
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
   RAWWAIT:begin a_addr={1'b0,raw_count};a_we=raw_response&&raw_hit&&raw_data[63:6]==0;a_w=raw_data[7:0];end
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
  if(kind==RAW)case(rec_i)
   0:out_byte=raw_at[7:0];1:out_byte={3'd0,raw_at[12:8]};2:out_byte=raw_count;default:begin end
  endcase
  if(kind==GEO||kind==ENDREC)begin
   if(rec_i==record_length-2)out_byte=checksum[7:0];
   if(rec_i==record_length-1)out_byte=checksum[15:8];
  end
 end
 assign byte_data=out_byte;
 task automatic emit_record(input kind_t k,input [7:0] n);
  begin kind<=k;record_length<=n;record_flush<=k==ENDREC;rec_i<=0;state<=REQUEST;end
 endtask
 task automatic next_block;
  begin
   if(cursor==4398)begin build_i<=0;state<=GEOTRAILER;end
   else begin
    block_id<=block_id+1'b1;row_i<=0;diff_count<=0;mask_acc<=0;left_row<=1;right_row<=1;
    row_size<=cursor<2112?66:cursor==4352?46:64;mask_bytes<=cursor<2112?9:cursor==4352?6:8;state<=FETCH;
   end
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;kind<=H;done<=0;fault<=0;base_valid<=0;cold<=1;raw_mode<=0;
   epoch<=0;base_serial<=0;generation<=0;checksum<=16'hffff;spans<=0;expanded<=0;
   cursor<=0;raw_at<=0;raw_limit<=0;block_id<=0;row_i<=0;row_size<=66;diff_count<=0;mask_bytes<=9;
   mask_acc<=0;new_byte<=0;old1<=0;old2<=0;new1<=0;new2<=0;edge0<=0;edge1<=0;
   left_row<=1;right_row<=1;shift_left<=0;rec_i<=0;build_i<=0;raw_count<=0;record_length<=0;record_flush<=0;
  end else begin
   done<=0;
   if(abort_source)begin fault<=4;base_valid<=0;end
   else if(state!=IDLE&&!lease_ok)begin fault<=2;base_valid<=0;end
   else if(!fault&&ack_valid&&state!=WAITACK&&state!=IDLE)begin fault<=5;base_valid<=0;end
   else if(!fault)case(state)
    IDLE:if(start)begin
     if(!frame_owned||!geometry_valid||frame_serial==0||frame_serial==32'hffffffff||
        (!base_valid&&frame_serial!=1)||(base_valid&&(content_epoch!=epoch||frame_serial!=serial)))begin fault<=1;base_valid<=0;end
     else begin
      epoch<=content_epoch;generation<=frame_generation;cold<=!base_valid;raw_limit<={2'd0,patch_count,8'd0};
      cursor<=0;block_id<=0;row_i<=0;row_size<=66;mask_bytes<=9;diff_count<=0;mask_acc<=0;left_row<=1;right_row<=1;
      checksum<=16'hffff;spans<=0;expanded<=0;build_i<=0;raw_mode<=0;state<=HEADER;
     end
    end
    HEADER:if(build_i==19)emit_record(H,20);else build_i<=build_i+1'b1;
    FETCH:if(in_valid)begin
     if(in_offset!=cursor||cursor>=4398)begin fault<=3;base_valid<=0;end else begin new_byte<=in_data;state<=FSTORE;end
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
     spans<=spans+1'b1;expanded<=expanded+(shift_ok?16'd66:{9'd0,diff_count});
     if(shift_ok)begin shift_left<=left_row;emit_record(SHIFT,4);end
     else emit_record(MASK,{1'b0,diff_count}+{4'd0,mask_bytes}+8'd1);
    end
    REQUEST:if(record_ready)state<=SREAD;
    SREAD:state<=SBYTE;
    SBYTE:if(byte_ready)begin
     if((kind!=GEO&&kind!=ENDREC)||rec_i<record_length-2)checksum<=crc16(checksum,byte_data);
     if(rec_i+1==record_length)case(kind)
      H:state<=FETCH;MASK,SHIFT:next_block();GEO:state<=RAWSTART;
      RAW:begin raw_at<=cursor;raw_count<=0;if(cursor==raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=RAWASK;end
      ENDREC:state<=WAITACK;default:begin fault<=6;base_valid<=0;end
     endcase
     else begin rec_i<=rec_i+1'b1;state<=SREAD;end
    end
    GEOTRAILER:if(build_i==7)emit_record(GEO,10);else build_i<=build_i+1'b1;
    RAWSTART:begin raw_mode<=1;cursor<=0;raw_at<=0;raw_count<=0;if(!raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=RAWASK;end
    RAWASK:state<=RAWWAIT;
    RAWWAIT:if(raw_response)begin
     if(!raw_hit||raw_data[63:6]!=0)begin fault<=3;base_valid<=0;end
     else begin cursor<=cursor+1'b1;raw_count<=raw_count+1'b1;state<=RAWCHECK;end
    end
    RAWCHECK:if(raw_count==240||cursor==raw_limit)emit_record(RAW,raw_count+8'd3);else state<=RAWASK;
    ENDTRAILER:if(build_i==3)emit_record(ENDREC,6);else build_i<=build_i+1'b1;
    WAITACK:if(ack_valid)begin
     if(!ack_accept||ack_generation!=generation)begin fault<=5;base_valid<=0;end
     else begin base_valid<=1;base_serial<=serial;done<=1;state<=IDLE;end
    end
    default:begin fault<=6;base_valid<=0;end
   endcase
  end
 end
endmodule
'''
