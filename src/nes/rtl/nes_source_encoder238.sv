// SPDX-License-Identifier: MIT
// Candidate N4 source encoder. Speculative base writes are NEVER reusable after
// abort, lease loss, bad ACK or transport failure: common sender/receiver reset
// is required. PREPARED admits the source base, not the SNES display commit.
// RAM payloads are unreset. Cold serial1 initializes every byte before reuse.
module nes_source_encoder238(
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
 localparam O=0,N=128,L=256,P=512,C=768,M=784;
 typedef enum logic [6:0] {IDLE,HEADER,REQUEST,SREAD,SBYTE,FETCH,FSTORE,
  COLDNEXT,COLDFLUSH,COLDDONE,DISPATCH,ROWREAD,ROWVALUE,ROWDECIDE,
  MAPLREAD,MAPLVALUE,MAPLNEXT,MAPFINISH,SHIFTBUILD,SHIFTDONE,
  DIRECTNEXT,LITERAL,LAPPEND,LAFTER,FLUSH,LH0,LH1,LH2,LDONE,
  COPYREAD,COPYWRITE,MASKREAD,MASKVALUE,MASKCHECK,MASKDECIDE,
  GROUPFINISH,GROUPOUT,CHEAPREAD,CHEAPVALUE,CHEAPDONE,GROUPDONE,
  MASKSETREAD,MASKSETVALUE,MASKSETWRITE,RASTERREAD,RASTERVALUE,RASTERNEXT,
  RASTERFINISH,RASTERBUILD,RASTERDONE,GEOTRAILER,RAWSTART,RAWASK,RAWWAIT,
  RAWNEXT,RAWFLUSH,RAWDONE,ENDTRAILER,WAITACK} state_t;
 // Constant state transitions let synthesis extract the main FSM. These
 // compact continuation tags are data, never dynamically assigned to state.
 state_t state;
 typedef enum logic [2:0] {S_FETCH,S_DISPATCH,S_FLUSH,S_GROUP,S_CHEAP,S_RAW,S_ACK} send_t;
 typedef enum logic [1:0] {C_SHIFT,C_LITERAL,C_RASTER,C_CHEAP} copy_t;
 typedef enum logic [2:0] {F_COLD,F_DISPATCH,F_AFTER,F_LITERAL,F_GROUP,F_RAW} flush_t;
 typedef enum logic [1:0] {L_DIRECT,L_MAP,L_RASTER} lit_t;
 send_t send_return;copy_t copy_return;flush_t flush_return;lit_t lit_return;
 (* ramstyle="M9K" *) reg [7:0] base[0:6143];
 (* ramstyle="M9K" *) reg [7:0] scratch[0:1023];
 reg [12:0] base_addr;reg base_we;reg [7:0] base_w,base_q;
 reg [9:0] a_addr,b_addr;reg a_we,b_we;reg [7:0] a_w,b_w,a_q,b_q;
 always @(posedge clk)begin
  base_q<=base[base_addr];if(base_we)base[base_addr]<=base_w;
 end
 // Separate port processes infer true dual-port M9K. The controller never
 // writes the same address on both ports; RAM contents have no reset path.
 always @(posedge clk)begin
  a_q<=scratch[a_addr];if(a_we)scratch[a_addr]<=a_w;
 end
 always @(posedge clk)begin
  b_q<=scratch[b_addr];if(b_we)scratch[b_addr]<=b_w;
 end
 reg base_valid,cold,crc_tail,raster_mode,raw_mode,cheap_target,expensive,mask_nonzero,mask_equal;
 reg equal_row,left_row,right_row;
 reg [31:0] epoch,serial,base_serial;
 reg [15:0] generation,checksum,spans,expanded;
 reg [12:0] cursor,row_start,lit_at,byte_at,group_start,raw_cursor,raw_limit;
 reg [7:0] new_byte,old_byte,old1,old2,new1,new2,xor_byte;
 reg [7:0] row_i,row_size,lit_len,lit_used,rows,rec_i,build_i,copy_n;
 reg [2:0] gap;
 reg [3:0] cheap_cost,cheap_i;
 reg [9:0] copy_from,copy_to,lit_target;
 wire lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 assign start_ready=!reset&&!abort_source&&!fault&&state==IDLE;
 assign in_ready=live&&state==FETCH;
 assign raw_query=live&&state==RAWASK;
 assign raw_index=raw_cursor;
 assign record_valid=live&&state==REQUEST;
 assign byte_valid=live&&state==SBYTE;
 assign byte_data=crc_tail&&rec_i==record_length-2?checksum[7:0]:
                  crc_tail&&rec_i==record_length-1?checksum[15:8]:a_q;
 assign ack_ready=live&&state==WAITACK;
 function automatic [15:0] crc16(input [15:0] previous,input [7:0] v);
  reg [15:0] c;integer i;begin c=previous^{v,8'd0};
   for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;
  end
 endfunction
 reg [7:0] header_byte;
 always @*begin
  case(build_i)
   0:header_byte="N";1:header_byte="4";2:header_byte=1;3:header_byte={7'd0,cold};
   4:header_byte=epoch[7:0];5:header_byte=epoch[15:8];6:header_byte=epoch[23:16];7:header_byte=epoch[31:24];
   8:header_byte=base_serial[7:0];9:header_byte=base_serial[15:8];10:header_byte=base_serial[23:16];11:header_byte=base_serial[31:24];
   12:header_byte=serial[7:0];13:header_byte=serial[15:8];14:header_byte=serial[23:16];15:header_byte=serial[31:24];
   16:header_byte=generation[7:0];17:header_byte=generation[15:8];default:header_byte=0;
  endcase
 end
 // One true dual-port scratch RAM. Reads are synchronous; every consumer has
 // an explicit read state. The 792-byte address span (635 payload bytes) is shared by all phases.
 always @*begin
  base_addr=cursor;base_we=0;base_w=new_byte;
  a_addr=0;b_addr=0;a_we=0;b_we=0;a_w=0;b_w=0;
  case(state)
   HEADER:begin a_addr={2'b10,build_i};a_we=1;a_w=header_byte;end
   SREAD,SBYTE:a_addr={2'b10,rec_i};
   FSTORE:begin
    base_we=live&&(cold||base_q!=new_byte);
    if(cold)begin a_addr={2'b01,lit_len};a_we=live;a_w=new_byte;end
    else if(cursor<2112||(cursor>=3872&&cursor<5664))begin
     a_addr={3'b000,row_i[6:0]};b_addr={3'b001,row_i[6:0]};a_we=live;b_we=live;a_w=base_q;b_w=new_byte;
    end
   end
   ROWREAD,ROWVALUE,MAPLREAD,MAPLVALUE,MASKREAD,MASKVALUE,MASKSETREAD,MASKSETVALUE,RASTERREAD,RASTERVALUE:
    begin a_addr={3'b000,row_i[6:0]};b_addr={3'b001,row_i[6:0]};end
   MASKCHECK:a_addr={7'b1100010,row_i[2:0]};
   MASKSETWRITE:begin a_addr={7'b1100010,row_i[2:0]};a_we=1;a_w=xor_byte;end
   LAPPEND:begin a_addr={2'b01,lit_len};a_we=1;a_w=new_byte;end
   LH0:begin a_addr=lit_target;a_we=1;a_w=lit_at[7:0];end
   LH1:begin a_addr=lit_target+1;a_we=1;a_w={3'd0,lit_at[12:8]};end
   LH2:begin a_addr=lit_target+2;a_we=1;a_w=lit_used;end
   COPYREAD,COPYWRITE:begin
    a_addr=copy_from;b_addr=copy_to;b_we=state==COPYWRITE;b_w=a_q;
   end
   SHIFTBUILD:begin
    a_addr={2'b10,build_i};a_we=1;
    case(build_i)0:a_w=row_start[7:0];1:a_w={3'd0,row_start[12:8]};2:a_w=0;3:a_w=2;default:a_w=left_row?1:255;endcase
   end
   RASTERBUILD:begin
    a_addr={2'b10,build_i};a_we=1;
    case(build_i)0:a_w=group_start[7:0];1:a_w={3'd0,group_start[12:8]};2:a_w=0;3:a_w=1;default:a_w=rows;endcase
   end
   CHEAPREAD,CHEAPVALUE:a_addr=C+cheap_i+2;
   GEOTRAILER,ENDTRAILER:begin
    a_addr={2'b10,build_i};a_we=1;
    case(build_i)
     0,1:a_w=255;2:a_w=0;3:a_w=state==GEOTRAILER?3:4;
     4:a_w=spans[7:0];5:a_w=spans[15:8];6:a_w=expanded[7:0];7:a_w=expanded[15:8];default:a_w=0;
    endcase
   end
   RAWWAIT:begin a_addr={2'b01,lit_len};a_we=live&&raw_response&&raw_hit&&raw_data[63:6]==0;a_w=raw_data[7:0];end
   default:begin end
  endcase
  if(!live)begin base_we=0;a_we=0;b_we=0;end
 end
 task automatic emit_record(input [7:0] size,input send_t next_state,input bit trailer,input bit last_record);
  begin record_length<=size;record_flush<=last_record;crc_tail<=trailer;send_return<=next_state;rec_i<=0;state<=REQUEST;end
 endtask
 task automatic copy_bytes(input [9:0] from_addr,to_addr,input [7:0] count,input copy_t next_state);
  begin copy_from<=from_addr;copy_to<=to_addr;copy_n<=count;copy_return<=next_state;state<=COPYREAD;end
 endtask
 task automatic resume_flush;
  case(flush_return)
   F_COLD:state<=COLDDONE;F_DISPATCH:state<=DISPATCH;F_AFTER:state<=LAFTER;
   F_LITERAL:state<=LITERAL;F_GROUP:state<=GROUPOUT;F_RAW:state<=RAWDONE;
   default:state<=IDLE;
  endcase
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;fault<=0;done<=0;base_valid<=0;epoch<=0;serial<=0;base_serial<=0;generation<=0;
   cursor<=0;row_start<=0;lit_at<=0;byte_at<=0;group_start<=0;raw_cursor<=0;raw_limit<=0;
   row_i<=0;row_size<=0;lit_len<=0;lit_used<=0;rows<=0;rec_i<=0;build_i<=0;copy_n<=0;
   gap<=0;cheap_cost<=0;cheap_i<=0;checksum<=16'hffff;spans<=0;expanded<=0;
   cold<=1;crc_tail<=0;raster_mode<=0;raw_mode<=0;cheap_target<=0;expensive<=0;mask_nonzero<=0;mask_equal<=0;
   equal_row<=0;left_row<=0;right_row<=0;new_byte<=0;old_byte<=0;old1<=0;old2<=0;new1<=0;new2<=0;xor_byte<=0;
   record_length<=0;record_flush<=0;copy_from<=0;copy_to<=0;lit_target<=0;
   send_return<=S_FETCH;copy_return<=C_SHIFT;flush_return<=F_COLD;lit_return<=L_DIRECT;
  end else begin
   done<=0;
   if(abort_source)begin fault<=4;base_valid<=0;end
   else if(state!=IDLE&&!lease_ok)begin fault<=2;base_valid<=0;end
   else if(!fault&&ack_valid&&state!=WAITACK&&state!=IDLE)begin fault<=5;base_valid<=0;end
   else if(!fault)case(state)
    IDLE:if(start)begin
     if(!frame_owned||!geometry_valid||frame_serial==0||frame_serial==32'hffffffff||
       (!base_valid&&frame_serial!=1)||(base_valid&&(content_epoch!=epoch||frame_serial!=base_serial+1)))begin fault<=1;base_valid<=0;end
     else begin
      epoch<=content_epoch;serial<=frame_serial;generation<=frame_generation;cold<=!base_valid;
      raw_limit<={2'd0,patch_count,8'd0};raw_cursor<=0;cursor<=0;row_i<=0;row_start<=0;row_size<=66;
      lit_at<=0;lit_len<=0;lit_used<=0;gap<=0;cheap_cost<=0;rows<=0;expensive<=0;mask_nonzero<=0;raster_mode<=0;raw_mode<=0;
      checksum<=16'hffff;spans<=0;expanded<=0;build_i<=0;state<=HEADER;
     end
    end
    HEADER:if(build_i==19)emit_record(20,S_FETCH,0,0);else build_i<=build_i+1'b1;
    REQUEST:if(record_ready)state<=SREAD;
    SREAD:state<=SBYTE;
    SBYTE:if(byte_ready)begin
     if(!crc_tail||rec_i<record_length-2)checksum<=crc16(checksum,byte_data);
     if(rec_i+1==record_length)begin
      case(send_return)
       S_FETCH:state<=FETCH;S_DISPATCH:state<=DISPATCH;S_FLUSH:resume_flush();
       S_GROUP:state<=GROUPDONE;S_CHEAP:state<=CHEAPREAD;S_RAW:state<=RAWSTART;S_ACK:state<=WAITACK;
       default:state<=IDLE;
      endcase
     end
     else begin rec_i<=rec_i+1'b1;state<=SREAD;end
    end
    FETCH:if(in_valid)begin
     if(in_offset!=cursor||cursor>=5741)begin fault<=3;base_valid<=0;end
     else begin new_byte<=in_data;state<=FSTORE;end
    end
    FSTORE:begin
     old_byte<=base_q;byte_at<=cursor;cursor<=cursor+1'b1;
     if(cold)begin lit_len<=lit_len+1'b1;lit_used<=lit_len+1'b1;state<=COLDNEXT;end
     else if(cursor<2112||(cursor>=3872&&cursor<5664))begin
      if(row_i+1==row_size)begin
       row_i<=0;equal_row<=1;left_row<=1;right_row<=1;mask_equal<=1;
       if(cursor<2112)state<=ROWREAD;else state<=MASKREAD;
      end else begin row_i<=row_i+1'b1;state<=FETCH;end
     end else begin lit_return<=L_DIRECT;state<=LITERAL;end
    end
    COLDNEXT:if(lit_len==240||cursor==5741)begin flush_return<=F_COLD;state<=FLUSH;end else state<=FETCH;
    COLDDONE:if(cursor==5741)begin build_i<=0;state<=GEOTRAILER;end else begin lit_at<=cursor;state<=FETCH;end
    DISPATCH:begin
     row_start<=cursor;row_i<=0;
     if(cursor==5741)begin build_i<=0;state<=GEOTRAILER;end
     else begin row_size<=cursor<2112?66:8;state<=FETCH;end
    end
    ROWREAD:state<=ROWVALUE;
    ROWVALUE:begin
     if(a_q!=b_q)equal_row<=0;
     if(row_i>=2)begin if(a_q!=new2)left_row<=0;if(b_q!=old2)right_row<=0;end
     old2<=old1;old1<=a_q;new2<=new1;new1<=b_q;
     if(row_i==65)begin row_i<=0;state<=ROWDECIDE;end else begin row_i<=row_i+1'b1;state<=ROWREAD;end
    end
    ROWDECIDE:if(equal_row)state<=DISPATCH;
     else if(left_row||right_row)begin build_i<=0;state<=SHIFTBUILD;end
     else state<=MAPLREAD;
    SHIFTBUILD:if(build_i==4)copy_bytes(N+(left_row?64:0),P+5,2,C_SHIFT);else build_i<=build_i+1'b1;
    SHIFTDONE:begin spans<=spans+1'b1;expanded<=expanded+66;emit_record(7,S_DISPATCH,0,0);end
    MAPLREAD:state<=MAPLVALUE;
    MAPLVALUE:begin old_byte<=a_q;new_byte<=b_q;byte_at<=row_start+row_i;lit_return<=L_MAP;state<=LITERAL;end
    MAPLNEXT:if(row_i==65)begin flush_return<=F_DISPATCH;state<=FLUSH;end
     else begin row_i<=row_i+1'b1;state<=MAPLREAD;end
    DIRECTNEXT:if(cursor==3872||cursor==5741)begin flush_return<=F_DISPATCH;state<=FLUSH;end else state<=FETCH;
    LITERAL:if(old_byte==new_byte)begin
     if(!lit_len)state<=LAFTER;
     else if(gap==3||lit_len==240)begin flush_return<=F_AFTER;state<=FLUSH;end
     else state<=LAPPEND;
    end else if(lit_len==240)begin flush_return<=F_LITERAL;state<=FLUSH;end else state<=LAPPEND;
    LAPPEND:begin
     if(!lit_len)lit_at<=byte_at;
     lit_len<=lit_len+1'b1;
     if(old_byte!=new_byte)begin lit_used<=lit_len+1'b1;gap<=0;end else gap<=gap+1'b1;
     if(raster_mode&&old_byte!=new_byte&&cheap_cost+4+lit_len>=13)begin
      expensive<=1;cheap_cost<=0;lit_len<=0;lit_used<=0;gap<=0;
     end
     state<=LAFTER;
    end
    LAFTER:case(lit_return)
     L_DIRECT:state<=DIRECTNEXT;L_MAP:state<=MAPLNEXT;L_RASTER:state<=RASTERNEXT;default:state<=IDLE;
    endcase
    FLUSH:if(!lit_used)begin lit_len<=0;gap<=0;resume_flush();end
     else if(raster_mode&&cheap_cost+3+lit_used>=13)begin
      expensive<=1;cheap_cost<=0;lit_len<=0;lit_used<=0;gap<=0;resume_flush();
     end else begin cheap_target<=raster_mode;lit_target<=raster_mode?C+cheap_cost:P;state<=LH0;end
    LH0:state<=LH1;
    LH1:state<=LH2;
    LH2:copy_bytes(L,lit_target+3,lit_used,C_LITERAL);
    LDONE:begin
     lit_len<=0;lit_used<=0;gap<=0;
     if(cheap_target)begin cheap_cost<=cheap_cost+3+lit_used;resume_flush();end
     else begin
      if(!raw_mode)begin spans<=spans+1'b1;expanded<=expanded+lit_used;end
      emit_record(lit_used+3,S_FLUSH,0,0);
     end
    end
    COPYREAD:state<=COPYWRITE;
    COPYWRITE:if(copy_n==1)begin
     case(copy_return)
      C_SHIFT:state<=SHIFTDONE;C_LITERAL:state<=LDONE;C_RASTER:state<=RASTERDONE;C_CHEAP:state<=CHEAPDONE;
     endcase
    end else begin copy_n<=copy_n-1'b1;copy_from<=copy_from+1'b1;copy_to<=copy_to+1'b1;state<=COPYREAD;end
    MASKREAD:state<=MASKVALUE;
    MASKVALUE:begin xor_byte<=a_q^b_q;state<=MASKCHECK;end
    MASKCHECK:begin // M is read on this edge; compare in MASKDECIDE.
     state<=MASKDECIDE;
    end
    MASKDECIDE:begin
     if(xor_byte!=a_q)mask_equal<=0;
     if(row_i==7)begin
      row_i<=0;
      if(!rows||!mask_equal||xor_byte!=a_q)state<=GROUPFINISH;
      else begin rows<=rows+1'b1;state<=RASTERREAD;end
     end else begin row_i<=row_i+1'b1;state<=MASKREAD;end
    end
    GROUPFINISH:begin flush_return<=F_GROUP;state<=FLUSH;end
    GROUPOUT:if(rows&&mask_nonzero&&expensive)begin build_i<=0;state<=RASTERBUILD;end
     else if(cheap_cost)begin cheap_i<=0;state<=CHEAPREAD;end else state<=GROUPDONE;
    RASTERBUILD:if(build_i==4)copy_bytes(M,P+5,8,C_RASTER);else build_i<=build_i+1'b1;
    RASTERDONE:begin spans<=spans+1'b1;expanded<=expanded+{5'd0,rows,3'd0};emit_record(13,S_GROUP,0,0);end
    CHEAPREAD:state<=CHEAPVALUE;
    CHEAPVALUE:begin record_length<=a_q+3;copy_bytes(C+cheap_i,P,a_q+3,C_CHEAP);end
    CHEAPDONE:begin
     spans<=spans+1'b1;expanded<=expanded+record_length-3;cheap_i<=cheap_i+record_length;
     emit_record(record_length,cheap_i+record_length==cheap_cost?S_GROUP:S_CHEAP,0,0);
    end
    GROUPDONE:begin
     cheap_cost<=0;expensive<=0;lit_len<=0;lit_used<=0;gap<=0;rows<=0;
     if(state==GROUPDONE&&row_start==5664)begin raster_mode<=0;state<=DISPATCH;end
     else begin row_i<=0;mask_nonzero<=0;group_start<=row_start;raster_mode<=1;state<=MASKSETREAD;end
    end
    MASKSETREAD:state<=MASKSETVALUE;
    MASKSETVALUE:begin xor_byte<=a_q^b_q;state<=MASKSETWRITE;end
    MASKSETWRITE:begin
     if(xor_byte)mask_nonzero<=1;
     if(row_i==7)begin row_i<=0;rows<=1;state<=RASTERREAD;end
     else begin row_i<=row_i+1'b1;state<=MASKSETREAD;end
    end
    RASTERREAD:if(expensive||!mask_nonzero)state<=RASTERFINISH;else state<=RASTERVALUE;
    RASTERVALUE:begin old_byte<=a_q;new_byte<=b_q;byte_at<=row_start+row_i;lit_return<=L_RASTER;state<=LITERAL;end
    RASTERNEXT:if(row_i==7||expensive)state<=RASTERFINISH;else begin row_i<=row_i+1'b1;state<=RASTERREAD;end
    RASTERFINISH:if(cursor==5664)begin row_start<=5664;state<=GROUPFINISH;end else state<=DISPATCH;
    GEOTRAILER:if(build_i==7)emit_record(10,S_RAW,1,0);else build_i<=build_i+1'b1;
    RAWSTART:begin raw_mode<=1;lit_at<=0;lit_len<=0;lit_used<=0;raw_cursor<=0;state<=RAWNEXT;end
    RAWNEXT:if(raw_cursor==raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=RAWASK;
    RAWASK:state<=RAWWAIT;
    RAWWAIT:if(raw_response)begin
     if(!raw_hit||raw_data[63:6]!=0)begin fault<=3;base_valid<=0;end
     else begin raw_cursor<=raw_cursor+1'b1;lit_len<=lit_len+1'b1;lit_used<=lit_len+1'b1;state<=RAWFLUSH;end
    end
    RAWFLUSH:if(lit_len==240||raw_cursor==raw_limit)begin flush_return<=F_RAW;state<=FLUSH;end else state<=RAWASK;
    RAWDONE:begin lit_at<=raw_cursor;state<=RAWNEXT;end
    ENDTRAILER:if(build_i==3)emit_record(6,S_ACK,1,1);else build_i<=build_i+1'b1;
    WAITACK:if(ack_valid)begin
     if(!ack_accept||ack_generation!=generation)begin fault<=5;base_valid<=0;end
     else begin base_valid<=1;base_serial<=serial;done<=1;state<=IDLE;end
    end
    default:begin fault<=6;base_valid<=0;end
   endcase
  end
 end
endmodule
