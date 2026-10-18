// SPDX-License-Identifier: MIT
// Candidate N4 source encoder. Speculative base writes are NEVER reusable after
// abort, lease loss, bad ACK or transport failure: common sender/receiver reset
// is required. PREPARED admits the source base, not the SNES display commit.
// RAM payloads are unreset. Cold serial1 initializes every byte before reuse.
module nes_source_encoder241(
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
 localparam O=0,N=128,L=256,P=208,C=80,M=96;
 typedef enum logic [6:0] {IDLE,HEADER,REQUEST,SREAD,SBYTE,FETCH,FSTORE,
  COLDNEXT,COLDFLUSH,COLDDONE,DISPATCH,ROWREAD,ROWVALUE,ROWDECIDE,
  MAPLREAD,MAPLVALUE,MAPLNEXT,MAPFINISH,SHIFTBUILD,SHIFTDONE,
  DIRECTNEXT,LITERAL,LAPPEND,LAFTER,FLUSH,LH0,LH1,LH2,LDONE,
  COPYREAD,COPYWRITE,CHEAPNEXT,MASKREAD,MASKVALUE,MASKCHECK,MASKDECIDE,
  GROUPFINISH,GROUPOUT,CHEAPREAD,CHEAPVALUE,CHEAPDONE,GROUPDONE,
  MASKSETREAD,MASKSETVALUE,MASKSETWRITE,RASTERREAD,RASTERVALUE,RASTERNEXT,
  RASTERFINISH,RASTERBUILD,RASTERDONE,GEOTRAILER,RAWSTART,RAWASK,RAWWAIT,
  RAWNEXT,RAWFLUSH,RAWDONE,ENDTRAILER,WAITACK} state_t;
 // The registered instruction and PC advance together. The ROM is read
 // at the resolved next PC, so synchronous M9K adds no execution bubble.
 reg [6:0] state;
 typedef enum logic [2:0] {S_FETCH,S_DISPATCH,S_FLUSH,S_GROUP,S_CHEAP,S_RAW,S_ACK} send_t;
 typedef enum logic [2:0] {F_COLD,F_DISPATCH,F_AFTER,F_LITERAL,F_GROUP,F_RAW} flush_t;
 typedef enum logic [1:0] {L_DIRECT,L_MAP,L_RASTER} lit_t;
 send_t send_return;flush_t flush_return;lit_t lit_return;
 // Power-of-two banks avoid the monolithic6144-depth eight-M9K mapping.
 (* ramstyle="M9K" *) reg [7:0] base_lo[0:4095];
 (* ramstyle="M9K" *) reg [7:0] base_hi[0:2047];
 (* ramstyle="M9K" *) reg [7:0] scratch[0:511];
 reg [12:0] base_addr;reg base_we;reg [7:0] base_w;
 reg [7:0] base_lo_q,base_hi_q;reg base_bank_q;
 wire [7:0] base_q=base_bank_q?base_hi_q:base_lo_q;
 reg [8:0] a_addr,b_addr;reg a_we,b_we;reg [7:0] a_w,b_w,a_q,b_q;
 always @(posedge clk)begin
  base_bank_q<=base_addr[12];
  base_lo_q<=base_lo[base_addr[11:0]];
  if(base_we&&!base_addr[12])base_lo[base_addr[11:0]]<=base_w;
 end
 always @(posedge clk)begin
  base_hi_q<=base_hi[base_addr[10:0]];
  if(base_we&&base_addr[12])base_hi[base_addr[10:0]]<=base_w;
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
 reg [31:0] epoch,base_serial;
 // Admission proves frame_serial==base_serial+1. The admitted base cannot
 // change until matching ACK, so this full-width value needs no second latch.
 wire [31:0] serial=base_serial+32'd1;
 reg [15:0] generation,checksum,spans,expanded;
 reg [12:0] cursor,row_start,lit_at,byte_at,group_start,raw_limit;
 reg [7:0] new_byte,old_byte,old1,old2,new1,new2,xor_byte;
 reg [7:0] row_i,row_size,lit_len,lit_used,rows,rec_i,build_i;
 reg [2:0] gap;
 reg [3:0] cheap_cost,cheap_i;
 // A record is a read-only view of header and existing payload storage.
 // send_return already distinguishes every view; no second mode register.
 // Only short cheap raster literals copy L into C, before record publication.
 wire [8:0] lit_target=cheap_target?C+cheap_cost:P;
 wire [7:0] payload_i=rec_i-8'd3;
 wire [7:0] special_i=rec_i-8'd5;
 reg [8:0] send_addr;
 always @*begin
  send_addr=P+rec_i;
  case(send_return)
   S_FLUSH:if(rec_i>=3)send_addr={1'b1,payload_i};
   S_DISPATCH:if(rec_i>=5)send_addr=N+(left_row?64:0)+special_i;
   S_GROUP:if(rec_i>=5)send_addr=M+special_i;
   S_CHEAP:send_addr=C+cheap_i+rec_i;
   default:begin end
  endcase
 end
 wire lease_ok=frame_owned&&geometry_valid&&generation==frame_generation;
 // 128 x 32 bits: yes PC7/no PC7/predicate6/RAM command5/interface7.
 // One 32-bit synchronous ROM is the resource hypothesis; MAP/FIT must prove it.
 (* ramstyle="M9K" *) reg [31:0] program_rom[0:127];
 reg [31:0] instruction;
 reg predicate;
 reg [6:0] resolved_pc,flush_pc,send_pc;
 wire [6:0] branch_pc=predicate?instruction[6:0]:instruction[13:7];
 wire control_step=!abort_source && !(state!=IDLE&&!lease_ok) &&
                   !(!fault&&ack_valid&&state!=WAITACK&&state!=IDLE) && !fault;
 wire [6:0] next_pc=reset?IDLE:control_step?resolved_pc:state;
 always @(posedge clk)begin
  state<=next_pc;
  instruction<=program_rom[next_pc];
 end
 localparam [6:0] J_SEND_BYTE=7'd96,J_STORE=7'd97,J_ROW=7'd98,J_SAME=7'd99,J_CHANGED=7'd100,J_LITERAL_RETURN=7'd101,J_FLUSH_RETURN=7'd102,J_MASK=7'd103,J_CHEAP=7'd104;
 localparam [4:0] R_NONE=0,R_HEADER=5'd1,R_SEND=5'd2,R_STORE=5'd3,R_ROW=5'd4,R_MASK_READ=5'd5,R_MASK_WRITE=5'd6,R_APPEND=5'd7,R_LH0=5'd8,R_LH1=5'd9,R_LH2=5'd10,R_COPY_READ=5'd11,R_COPY_WRITE=5'd12,R_SHIFT=5'd13,R_RASTER=5'd14,R_CHEAP=5'd15,R_TRAILER=5'd16,R_RAW=5'd17;
 wire [4:0] ram_command=instruction[24:20];
 integer pc_init;
 initial begin
  for(pc_init=0;pc_init<128;pc_init=pc_init+1)program_rom[pc_init]={18'd0,pc_init[6:0],pc_init[6:0]};
  program_rom[IDLE]={7'd0,5'd0,6'd1,7'(IDLE),7'(HEADER)};
  program_rom[HEADER]={7'd0,5'd1,6'd2,7'(HEADER),7'(REQUEST)};
  program_rom[REQUEST]={7'd2,5'd0,6'd3,7'(REQUEST),7'(SREAD)};
  program_rom[SREAD]={7'd4,5'd2,6'd0,7'(SREAD),7'(SBYTE)};
  program_rom[SBYTE]={7'd8,5'd2,6'd4,7'(SBYTE),7'(J_SEND_BYTE)};
  program_rom[FETCH]={7'd1,5'd0,6'd5,7'(FETCH),7'(FSTORE)};
  program_rom[FSTORE]={7'd0,5'd3,6'd6,7'(J_STORE),7'(COLDNEXT)};
  program_rom[COLDNEXT]={7'd0,5'd0,6'd7,7'(FETCH),7'(FLUSH)};
  program_rom[COLDDONE]={7'd0,5'd0,6'd8,7'(FETCH),7'(GEOTRAILER)};
  program_rom[DISPATCH]={7'd0,5'd0,6'd8,7'(FETCH),7'(GEOTRAILER)};
  program_rom[ROWREAD]={7'd0,5'd4,6'd0,7'(ROWREAD),7'(ROWVALUE)};
  program_rom[ROWVALUE]={7'd0,5'd4,6'd9,7'(ROWREAD),7'(ROWDECIDE)};
  program_rom[ROWDECIDE]={7'd0,5'd0,6'd10,7'(J_ROW),7'(DISPATCH)};
  program_rom[SHIFTBUILD]={7'd0,5'd13,6'd11,7'(SHIFTBUILD),7'(SHIFTDONE)};
  program_rom[SHIFTDONE]={7'd0,5'd0,6'd0,7'(SHIFTDONE),7'(REQUEST)};
  program_rom[MAPLREAD]={7'd0,5'd4,6'd0,7'(MAPLREAD),7'(MAPLVALUE)};
  program_rom[MAPLVALUE]={7'd0,5'd4,6'd0,7'(MAPLVALUE),7'(LITERAL)};
  program_rom[MAPLNEXT]={7'd0,5'd0,6'd9,7'(MAPLREAD),7'(FLUSH)};
  program_rom[DIRECTNEXT]={7'd0,5'd0,6'd12,7'(FETCH),7'(FLUSH)};
  program_rom[LITERAL]={7'd0,5'd0,6'd13,7'(J_CHANGED),7'(J_SAME)};
  program_rom[LAPPEND]={7'd0,5'd7,6'd0,7'(LAPPEND),7'(LAFTER)};
  program_rom[LAFTER]={7'd0,5'd0,6'd0,7'(LAFTER),7'(J_LITERAL_RETURN)};
  program_rom[FLUSH]={7'd0,5'd0,6'd14,7'(LH0),7'(J_FLUSH_RETURN)};
  program_rom[LH0]={7'd0,5'd8,6'd0,7'(LH0),7'(LH1)};
  program_rom[LH1]={7'd0,5'd9,6'd0,7'(LH1),7'(LH2)};
  program_rom[LH2]={7'd0,5'd10,6'd15,7'(LDONE),7'(COPYREAD)};
  program_rom[LDONE]={7'd0,5'd0,6'd15,7'(REQUEST),7'(J_FLUSH_RETURN)};
  program_rom[COPYREAD]={7'd0,5'd11,6'd0,7'(COPYREAD),7'(COPYWRITE)};
  program_rom[COPYWRITE]={7'd0,5'd12,6'd16,7'(COPYREAD),7'(LDONE)};
  program_rom[MASKREAD]={7'd0,5'd4,6'd0,7'(MASKREAD),7'(MASKVALUE)};
  program_rom[MASKVALUE]={7'd0,5'd4,6'd0,7'(MASKVALUE),7'(MASKCHECK)};
  program_rom[MASKCHECK]={7'd0,5'd5,6'd0,7'(MASKCHECK),7'(MASKDECIDE)};
  program_rom[MASKDECIDE]={7'd0,5'd0,6'd17,7'(MASKREAD),7'(J_MASK)};
  program_rom[GROUPFINISH]={7'd0,5'd0,6'd0,7'(GROUPFINISH),7'(FLUSH)};
  program_rom[GROUPOUT]={7'd0,5'd0,6'd18,7'(J_CHEAP),7'(RASTERBUILD)};
  program_rom[RASTERBUILD]={7'd0,5'd14,6'd11,7'(RASTERBUILD),7'(RASTERDONE)};
  program_rom[RASTERDONE]={7'd0,5'd0,6'd0,7'(RASTERDONE),7'(REQUEST)};
  program_rom[CHEAPREAD]={7'd0,5'd15,6'd0,7'(CHEAPREAD),7'(CHEAPVALUE)};
  program_rom[CHEAPVALUE]={7'd0,5'd15,6'd0,7'(CHEAPVALUE),7'(CHEAPDONE)};
  program_rom[CHEAPDONE]={7'd0,5'd0,6'd0,7'(CHEAPDONE),7'(REQUEST)};
  program_rom[CHEAPNEXT]={7'd0,5'd0,6'd19,7'(CHEAPREAD),7'(GROUPDONE)};
  program_rom[GROUPDONE]={7'd0,5'd0,6'd20,7'(MASKSETREAD),7'(DISPATCH)};
  program_rom[MASKSETREAD]={7'd0,5'd4,6'd0,7'(MASKSETREAD),7'(MASKSETVALUE)};
  program_rom[MASKSETVALUE]={7'd0,5'd4,6'd0,7'(MASKSETVALUE),7'(MASKSETWRITE)};
  program_rom[MASKSETWRITE]={7'd0,5'd6,6'd17,7'(MASKSETREAD),7'(RASTERREAD)};
  program_rom[RASTERREAD]={7'd0,5'd4,6'd21,7'(RASTERVALUE),7'(RASTERFINISH)};
  program_rom[RASTERVALUE]={7'd0,5'd4,6'd0,7'(RASTERVALUE),7'(LITERAL)};
  program_rom[RASTERNEXT]={7'd0,5'd0,6'd22,7'(RASTERREAD),7'(RASTERFINISH)};
  program_rom[RASTERFINISH]={7'd0,5'd0,6'd23,7'(DISPATCH),7'(GROUPFINISH)};
  program_rom[GEOTRAILER]={7'd0,5'd16,6'd24,7'(GEOTRAILER),7'(REQUEST)};
  program_rom[RAWSTART]={7'd0,5'd0,6'd0,7'(RAWSTART),7'(RAWNEXT)};
  program_rom[RAWNEXT]={7'd0,5'd0,6'd25,7'(RAWASK),7'(ENDTRAILER)};
  program_rom[RAWASK]={7'd16,5'd0,6'd0,7'(RAWASK),7'(RAWWAIT)};
  program_rom[RAWWAIT]={7'd32,5'd17,6'd26,7'(RAWWAIT),7'(RAWFLUSH)};
  program_rom[RAWFLUSH]={7'd0,5'd0,6'd27,7'(RAWASK),7'(FLUSH)};
  program_rom[RAWDONE]={7'd0,5'd0,6'd0,7'(RAWDONE),7'(RAWNEXT)};
  program_rom[ENDTRAILER]={7'd0,5'd16,6'd28,7'(ENDTRAILER),7'(REQUEST)};
  program_rom[WAITACK]={7'd64,5'd0,6'd29,7'(WAITACK),7'(IDLE)};
 end
 always @*begin
  case(instruction[19:14])
   6'd0:predicate=(1'b1);
   6'd1:predicate=(start && frame_owned && geometry_valid && frame_serial!=0 && frame_serial!=32'hffffffff && ((!base_valid && frame_serial==1)||(base_valid && content_epoch==epoch && frame_serial==serial)));
   6'd2:predicate=(build_i==19);
   6'd3:predicate=(record_ready);
   6'd4:predicate=(byte_ready);
   6'd5:predicate=(in_valid && in_offset==cursor && cursor<5741);
   6'd6:predicate=(cold);
   6'd7:predicate=(lit_len==240 || cursor==5741);
   6'd8:predicate=(cursor==5741);
   6'd9:predicate=(row_i==65);
   6'd10:predicate=(equal_row);
   6'd11:predicate=(build_i==4);
   6'd12:predicate=(cursor==3872 || cursor==5741);
   6'd13:predicate=(old_byte==new_byte);
   6'd14:predicate=(!lit_used || (raster_mode && cheap_cost+3+lit_used>=13));
   6'd15:predicate=(cheap_target);
   6'd16:predicate=(build_i+1==lit_used);
   6'd17:predicate=(row_i==7);
   6'd18:predicate=(rows && mask_nonzero && expensive);
   6'd19:predicate=(cheap_i+record_length==cheap_cost);
   6'd20:predicate=(row_start==5664);
   6'd21:predicate=(expensive || !mask_nonzero);
   6'd22:predicate=(row_i==7 || expensive);
   6'd23:predicate=(cursor==5664);
   6'd24:predicate=(build_i==7);
   6'd25:predicate=(cursor==raw_limit);
   6'd26:predicate=(raw_response && raw_hit && raw_data[63:6]==0);
   6'd27:predicate=(lit_len==240 || cursor==raw_limit);
   6'd28:predicate=(build_i==3);
   6'd29:predicate=(ack_valid && ack_accept && ack_generation==generation);
   default:predicate=0;
  endcase
 end
 always @*begin
  case(flush_return)
   F_COLD:flush_pc=COLDDONE;F_DISPATCH:flush_pc=DISPATCH;F_AFTER:flush_pc=LAFTER;
   F_LITERAL:flush_pc=LITERAL;F_GROUP:flush_pc=GROUPOUT;F_RAW:flush_pc=RAWDONE;
   default:flush_pc=IDLE;
  endcase
  case(send_return)
   S_FETCH:send_pc=FETCH;S_DISPATCH:send_pc=DISPATCH;S_FLUSH:send_pc=flush_pc;
   S_GROUP:send_pc=GROUPDONE;S_CHEAP:send_pc=CHEAPNEXT;S_RAW:send_pc=RAWSTART;S_ACK:send_pc=WAITACK;
   default:send_pc=IDLE;
  endcase
  resolved_pc=branch_pc;
  case(branch_pc)
   J_SEND_BYTE:resolved_pc=rec_i+1==record_length?send_pc:SREAD;
   J_STORE:if(cursor<2112||(cursor>=3872&&cursor<5664))
      resolved_pc=row_i+1==row_size?(cursor<2112?ROWREAD:MASKREAD):FETCH;
     else resolved_pc=LITERAL;
   J_ROW:resolved_pc=left_row||right_row?SHIFTBUILD:MAPLREAD;
   J_SAME:resolved_pc=!lit_len?LAFTER:(gap==3||lit_len==240?FLUSH:LAPPEND);
   J_CHANGED:resolved_pc=lit_len==240?FLUSH:LAPPEND;
   J_LITERAL_RETURN:case(lit_return)
    L_DIRECT:resolved_pc=DIRECTNEXT;L_MAP:resolved_pc=MAPLNEXT;L_RASTER:resolved_pc=RASTERNEXT;default:resolved_pc=IDLE;
   endcase
   J_FLUSH_RETURN:resolved_pc=flush_pc;
   J_MASK:resolved_pc=!rows||!mask_equal||xor_byte!=a_q?GROUPFINISH:RASTERREAD;
   J_CHEAP:resolved_pc=cheap_cost?CHEAPREAD:GROUPDONE;
   default:begin end
  endcase
 end
 wire live=!reset&&!abort_source&&!fault&&lease_ok;
 assign start_ready=!reset&&!abort_source&&!fault&&state==IDLE;
 assign in_ready=live&&instruction[25];
 assign raw_query=live&&instruction[29];
 assign raw_index=cursor;
 assign record_valid=live&&instruction[26];
 assign byte_valid=live&&instruction[28];
 assign byte_data=crc_tail&&rec_i==record_length-2?checksum[7:0]:
                  crc_tail&&rec_i==record_length-1?checksum[15:8]:a_q;
 assign ack_ready=live&&instruction[31];
 function automatic [15:0] crc16(input [15:0] previous,input [7:0] v);
  reg [15:0] c;integer i;begin c=previous^{v,8'd0};
   for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc16=c;
  end
 endfunction
 reg [15:0] expanded_delta;
 always @*begin
  case(state)
   SHIFTDONE:expanded_delta=16'd66;
   RASTERDONE:expanded_delta={5'd0,rows,3'd0};
   CHEAPDONE:expanded_delta={8'd0,record_length}-16'd3;
   default:expanded_delta={8'd0,lit_used};
  endcase
 end
 wire count_geometry=state==SHIFTDONE||state==RASTERDONE||state==CHEAPDONE||
                     (state==LDONE&&!cheap_target&&!raw_mode);
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
 // an explicit read state. The 496-byte address span (412 payload bytes) is shared by all phases.
 always @*begin
  base_addr=cursor;base_we=0;base_w=new_byte;
  a_addr=0;b_addr=0;a_we=0;b_we=0;a_w=0;b_w=0;
  case(ram_command)
   R_HEADER:begin a_addr=P+build_i;a_we=1;a_w=header_byte;end
   R_SEND:a_addr=send_addr;
   R_STORE:begin
    base_we=live&&(cold||base_q!=new_byte);
    if(cold)begin a_addr={1'b1,lit_len};a_we=live;a_w=new_byte;end
    else if(cursor<2112||(cursor>=3872&&cursor<5664))begin
     a_addr={2'b00,row_i[6:0]};b_addr={2'b01,row_i[6:0]};a_we=live;b_we=live;a_w=base_q;b_w=new_byte;
    end
   end
   R_ROW:
    begin a_addr={2'b00,row_i[6:0]};b_addr={2'b01,row_i[6:0]};end
   R_MASK_READ:a_addr={6'b001100,row_i[2:0]};
   R_MASK_WRITE:begin a_addr={6'b001100,row_i[2:0]};a_we=1;a_w=xor_byte;end
   R_APPEND:begin a_addr={1'b1,lit_len};a_we=1;a_w=new_byte;end
   R_LH0:begin a_addr=lit_target;a_we=1;a_w=lit_at[7:0];end
   R_LH1:begin a_addr=lit_target+1;a_we=1;a_w={3'd0,lit_at[12:8]};end
   R_LH2:begin a_addr=lit_target+2;a_we=1;a_w=lit_used;end
   R_COPY_READ,R_COPY_WRITE:begin
    a_addr={1'b1,build_i};b_addr=C+cheap_cost+3+build_i;b_we=ram_command==R_COPY_WRITE;b_w=a_q;
   end
   R_SHIFT:begin
    a_addr=P+build_i;a_we=1;
    case(build_i)0:a_w=row_start[7:0];1:a_w={3'd0,row_start[12:8]};2:a_w=0;3:a_w=2;default:a_w=left_row?1:255;endcase
   end
   R_RASTER:begin
    a_addr=P+build_i;a_we=1;
    case(build_i)0:a_w=group_start[7:0];1:a_w={3'd0,group_start[12:8]};2:a_w=0;3:a_w=1;default:a_w=rows;endcase
   end
   R_CHEAP:a_addr=C+cheap_i+2;
   R_TRAILER:begin
    a_addr=P+build_i;a_we=1;
    case(build_i)
     0,1:a_w=255;2:a_w=0;3:a_w=state==GEOTRAILER?3:4;
     4:a_w=spans[7:0];5:a_w=spans[15:8];6:a_w=expanded[7:0];7:a_w=expanded[15:8];default:a_w=0;
    endcase
   end
   R_RAW:begin a_addr={1'b1,lit_len};a_we=live&&raw_response&&raw_hit&&raw_data[63:6]==0;a_w=raw_data[7:0];end
   default:begin end
  endcase
  if(!live)begin base_we=0;a_we=0;b_we=0;end
 end
 // No hardware: annotations retain the old datapath branch skeleton.
 // Cycle-exact reference240 checks independently verify the real ROM PC.
 task automatic pc_annotation(input [6:0] destination);begin end endtask
 task automatic emit_record(input [7:0] size,input send_t next_state,input bit trailer,input bit last_record);
  begin record_length<=size;record_flush<=last_record;crc_tail<=trailer;send_return<=next_state;rec_i<=0;pc_annotation(REQUEST);end
 endtask
 task automatic resume_flush;
  case(flush_return)
   F_COLD:pc_annotation(COLDDONE);F_DISPATCH:pc_annotation(DISPATCH);F_AFTER:pc_annotation(LAFTER);
   F_LITERAL:pc_annotation(LITERAL);F_GROUP:pc_annotation(GROUPOUT);F_RAW:pc_annotation(RAWDONE);
   default:pc_annotation(IDLE);
  endcase
 endtask
 always @(posedge clk)begin
  if(reset)begin
   pc_annotation(IDLE);fault<=0;done<=0;base_valid<=0;epoch<=0;base_serial<=0;generation<=0;
   cursor<=0;row_start<=0;lit_at<=0;byte_at<=0;group_start<=0;raw_limit<=0;
   row_i<=0;row_size<=0;lit_len<=0;lit_used<=0;rows<=0;rec_i<=0;build_i<=0;
   gap<=0;cheap_cost<=0;cheap_i<=0;checksum<=16'hffff;spans<=0;expanded<=0;
   cold<=1;crc_tail<=0;raster_mode<=0;raw_mode<=0;cheap_target<=0;expensive<=0;mask_nonzero<=0;mask_equal<=0;
   equal_row<=0;left_row<=0;right_row<=0;new_byte<=0;old_byte<=0;old1<=0;old2<=0;new1<=0;new2<=0;xor_byte<=0;
   record_length<=0;record_flush<=0;
   send_return<=S_FETCH;flush_return<=F_COLD;lit_return<=L_DIRECT;
  end else begin
   done<=0;
   if(abort_source)begin fault<=4;base_valid<=0;end
   else if(state!=IDLE&&!lease_ok)begin fault<=2;base_valid<=0;end
   else if(!fault&&ack_valid&&state!=WAITACK&&state!=IDLE)begin fault<=5;base_valid<=0;end
   else if(!fault)begin
    if(count_geometry)begin spans<=spans+1'b1;expanded<=expanded+expanded_delta;end
    case(state)
    IDLE:if(start)begin
     if(!frame_owned||!geometry_valid||frame_serial==0||frame_serial==32'hffffffff||
       (!base_valid&&frame_serial!=1)||(base_valid&&(content_epoch!=epoch||frame_serial!=serial)))begin fault<=1;base_valid<=0;end
     else begin
      epoch<=content_epoch;generation<=frame_generation;cold<=!base_valid;
      raw_limit<={2'd0,patch_count,8'd0};cursor<=0;row_i<=0;row_start<=0;row_size<=66;
      lit_at<=0;lit_len<=0;lit_used<=0;gap<=0;cheap_cost<=0;rows<=0;expensive<=0;mask_nonzero<=0;raster_mode<=0;raw_mode<=0;
      checksum<=16'hffff;spans<=0;expanded<=0;build_i<=0;pc_annotation(HEADER);
     end
    end
    HEADER:if(build_i==19)emit_record(20,S_FETCH,0,0);else build_i<=build_i+1'b1;
    REQUEST:if(record_ready)pc_annotation(SREAD);
    SREAD:pc_annotation(SBYTE);
    SBYTE:if(byte_ready)begin
     if(!crc_tail||rec_i<record_length-2)checksum<=crc16(checksum,byte_data);
     if(rec_i+1==record_length)begin
      case(send_return)
       S_FETCH:pc_annotation(FETCH);S_DISPATCH:pc_annotation(DISPATCH);S_FLUSH:resume_flush();
       S_GROUP:pc_annotation(GROUPDONE);S_CHEAP:pc_annotation(CHEAPNEXT);S_RAW:pc_annotation(RAWSTART);S_ACK:pc_annotation(WAITACK);
       default:pc_annotation(IDLE);
      endcase
     end
     else begin rec_i<=rec_i+1'b1;pc_annotation(SREAD);end
    end
    FETCH:if(in_valid)begin
     if(in_offset!=cursor||cursor>=5741)begin fault<=3;base_valid<=0;end
     else begin new_byte<=in_data;pc_annotation(FSTORE);end
    end
    FSTORE:begin
     old_byte<=base_q;byte_at<=cursor;cursor<=cursor+1'b1;
     if(cold)begin lit_len<=lit_len+1'b1;lit_used<=lit_len+1'b1;pc_annotation(COLDNEXT);end
     else if(cursor<2112||(cursor>=3872&&cursor<5664))begin
      if(row_i+1==row_size)begin
       row_i<=0;equal_row<=1;left_row<=1;right_row<=1;mask_equal<=1;
       if(cursor<2112)pc_annotation(ROWREAD);else pc_annotation(MASKREAD);
      end else begin row_i<=row_i+1'b1;pc_annotation(FETCH);end
     end else begin lit_return<=L_DIRECT;pc_annotation(LITERAL);end
    end
    COLDNEXT:if(lit_len==240||cursor==5741)begin flush_return<=F_COLD;pc_annotation(FLUSH);end else pc_annotation(FETCH);
    COLDDONE:if(cursor==5741)begin build_i<=0;pc_annotation(GEOTRAILER);end else begin lit_at<=cursor;pc_annotation(FETCH);end
    DISPATCH:begin
     row_start<=cursor;row_i<=0;
     if(cursor==5741)begin build_i<=0;pc_annotation(GEOTRAILER);end
     else begin row_size<=cursor<2112?66:8;pc_annotation(FETCH);end
    end
    ROWREAD:pc_annotation(ROWVALUE);
    ROWVALUE:begin
     if(a_q!=b_q)equal_row<=0;
     if(row_i>=2)begin if(a_q!=new2)left_row<=0;if(b_q!=old2)right_row<=0;end
     old2<=old1;old1<=a_q;new2<=new1;new1<=b_q;
     if(row_i==65)begin row_i<=0;pc_annotation(ROWDECIDE);end else begin row_i<=row_i+1'b1;pc_annotation(ROWREAD);end
    end
    ROWDECIDE:if(equal_row)pc_annotation(DISPATCH);
     else if(left_row||right_row)begin build_i<=0;pc_annotation(SHIFTBUILD);end
     else pc_annotation(MAPLREAD);
    SHIFTBUILD:if(build_i==4)pc_annotation(SHIFTDONE);else build_i<=build_i+1'b1;
    SHIFTDONE:begin emit_record(7,S_DISPATCH,0,0);end
    MAPLREAD:pc_annotation(MAPLVALUE);
    MAPLVALUE:begin old_byte<=a_q;new_byte<=b_q;byte_at<=row_start+row_i;lit_return<=L_MAP;pc_annotation(LITERAL);end
    MAPLNEXT:if(row_i==65)begin flush_return<=F_DISPATCH;pc_annotation(FLUSH);end
     else begin row_i<=row_i+1'b1;pc_annotation(MAPLREAD);end
    DIRECTNEXT:if(cursor==3872||cursor==5741)begin flush_return<=F_DISPATCH;pc_annotation(FLUSH);end else pc_annotation(FETCH);
    LITERAL:if(old_byte==new_byte)begin
     if(!lit_len)pc_annotation(LAFTER);
     else if(gap==3||lit_len==240)begin flush_return<=F_AFTER;pc_annotation(FLUSH);end
     else pc_annotation(LAPPEND);
    end else if(lit_len==240)begin flush_return<=F_LITERAL;pc_annotation(FLUSH);end else pc_annotation(LAPPEND);
    LAPPEND:begin
     if(!lit_len)lit_at<=byte_at;
     lit_len<=lit_len+1'b1;
     if(old_byte!=new_byte)begin lit_used<=lit_len+1'b1;gap<=0;end else gap<=gap+1'b1;
     if(raster_mode&&old_byte!=new_byte&&cheap_cost+4+lit_len>=13)begin
      expensive<=1;cheap_cost<=0;lit_len<=0;lit_used<=0;gap<=0;
     end
     pc_annotation(LAFTER);
    end
    LAFTER:case(lit_return)
     L_DIRECT:pc_annotation(DIRECTNEXT);L_MAP:pc_annotation(MAPLNEXT);L_RASTER:pc_annotation(RASTERNEXT);default:pc_annotation(IDLE);
    endcase
    FLUSH:if(!lit_used)begin lit_len<=0;gap<=0;resume_flush();end
     else if(raster_mode&&cheap_cost+3+lit_used>=13)begin
      expensive<=1;cheap_cost<=0;lit_len<=0;lit_used<=0;gap<=0;resume_flush();
     end else begin cheap_target<=raster_mode;pc_annotation(LH0);end
    LH0:pc_annotation(LH1);
    LH1:pc_annotation(LH2);
    LH2:if(cheap_target)begin build_i<=0;pc_annotation(COPYREAD);end else pc_annotation(LDONE);
    LDONE:begin
     lit_len<=0;lit_used<=0;gap<=0;
     if(cheap_target)begin cheap_cost<=cheap_cost+3+lit_used;resume_flush();end
     else begin

      emit_record(lit_used+3,S_FLUSH,0,0);
     end
    end
    COPYREAD:pc_annotation(COPYWRITE);
    COPYWRITE:if(build_i+1==lit_used)pc_annotation(LDONE);
     else begin build_i<=build_i+1'b1;pc_annotation(COPYREAD);end
    MASKREAD:pc_annotation(MASKVALUE);
    MASKVALUE:begin xor_byte<=a_q^b_q;pc_annotation(MASKCHECK);end
    MASKCHECK:begin // M is read on this edge; compare in MASKDECIDE.
     pc_annotation(MASKDECIDE);
    end
    MASKDECIDE:begin
     if(xor_byte!=a_q)mask_equal<=0;
     if(row_i==7)begin
      row_i<=0;
      if(!rows||!mask_equal||xor_byte!=a_q)pc_annotation(GROUPFINISH);
      else begin rows<=rows+1'b1;pc_annotation(RASTERREAD);end
     end else begin row_i<=row_i+1'b1;pc_annotation(MASKREAD);end
    end
    GROUPFINISH:begin flush_return<=F_GROUP;pc_annotation(FLUSH);end
    GROUPOUT:if(rows&&mask_nonzero&&expensive)begin build_i<=0;pc_annotation(RASTERBUILD);end
     else if(cheap_cost)begin cheap_i<=0;pc_annotation(CHEAPREAD);end else pc_annotation(GROUPDONE);
    RASTERBUILD:if(build_i==4)pc_annotation(RASTERDONE);else build_i<=build_i+1'b1;
    RASTERDONE:begin emit_record(13,S_GROUP,0,0);end
    CHEAPREAD:pc_annotation(CHEAPVALUE);
    CHEAPVALUE:begin record_length<=a_q+3;pc_annotation(CHEAPDONE);end
    CHEAPDONE:emit_record(record_length,S_CHEAP,0,0);
    CHEAPNEXT:begin
     cheap_i<=cheap_i+record_length;
     if(cheap_i+record_length==cheap_cost)pc_annotation(GROUPDONE);else pc_annotation(CHEAPREAD);
    end
    GROUPDONE:begin
     cheap_cost<=0;expensive<=0;lit_len<=0;lit_used<=0;gap<=0;rows<=0;
     if(state==GROUPDONE&&row_start==5664)begin raster_mode<=0;pc_annotation(DISPATCH);end
     else begin row_i<=0;mask_nonzero<=0;group_start<=row_start;raster_mode<=1;pc_annotation(MASKSETREAD);end
    end
    MASKSETREAD:pc_annotation(MASKSETVALUE);
    MASKSETVALUE:begin xor_byte<=a_q^b_q;pc_annotation(MASKSETWRITE);end
    MASKSETWRITE:begin
     if(xor_byte)mask_nonzero<=1;
     if(row_i==7)begin row_i<=0;rows<=1;pc_annotation(RASTERREAD);end
     else begin row_i<=row_i+1'b1;pc_annotation(MASKSETREAD);end
    end
    RASTERREAD:if(expensive||!mask_nonzero)pc_annotation(RASTERFINISH);else pc_annotation(RASTERVALUE);
    RASTERVALUE:begin old_byte<=a_q;new_byte<=b_q;byte_at<=row_start+row_i;lit_return<=L_RASTER;pc_annotation(LITERAL);end
    RASTERNEXT:if(row_i==7||expensive)pc_annotation(RASTERFINISH);else begin row_i<=row_i+1'b1;pc_annotation(RASTERREAD);end
    RASTERFINISH:if(cursor==5664)begin row_start<=5664;pc_annotation(GROUPFINISH);end else pc_annotation(DISPATCH);
    GEOTRAILER:if(build_i==7)emit_record(10,S_RAW,1,0);else build_i<=build_i+1'b1;
    RAWSTART:begin raw_mode<=1;lit_at<=0;lit_len<=0;lit_used<=0;cursor<=0;pc_annotation(RAWNEXT);end
    RAWNEXT:if(cursor==raw_limit)begin build_i<=0;pc_annotation(ENDTRAILER);end else pc_annotation(RAWASK);
    RAWASK:pc_annotation(RAWWAIT);
    RAWWAIT:if(raw_response)begin
     if(!raw_hit||raw_data[63:6]!=0)begin fault<=3;base_valid<=0;end
     else begin cursor<=cursor+1'b1;lit_len<=lit_len+1'b1;lit_used<=lit_len+1'b1;pc_annotation(RAWFLUSH);end
    end
    RAWFLUSH:if(lit_len==240||cursor==raw_limit)begin flush_return<=F_RAW;pc_annotation(FLUSH);end else pc_annotation(RAWASK);
    RAWDONE:begin lit_at<=cursor;pc_annotation(RAWNEXT);end
    ENDTRAILER:if(build_i==3)emit_record(6,S_ACK,1,1);else build_i<=build_i+1'b1;
    WAITACK:if(ack_valid)begin
     if(!ack_accept||ack_generation!=generation)begin fault<=5;base_valid<=0;end
     else begin base_valid<=1;base_serial<=serial;done<=1;pc_annotation(IDLE);end
    end
    default:begin fault<=6;base_valid<=0;end
   endcase
   end
  end
 end
endmodule
