// SPDX-License-Identifier: MIT
// One4KiB payload RAM: unpublished TILE ring3584B + ordinary512B.
// No DMA descriptor is manufactured by prefill. Canonical stamps are checked
// against the immutable ARM record before the source aperture is published.
module nes_stage396(input wire clk,reset,active,
 input wire begin_valid,begin_tile,input wire [11:0] begin_length,input wire [31:0] begin_token,
 input wire [15:0] generation,input wire kind,input wire [9:0] first,
 output wire begin_ready,input wire byte_valid,input wire [7:0] byte_data,output wire byte_ready,input wire seal,
 output reg producer_error,output wire chunk_ready,
 input wire consume,input wire [31:0] consume_token,output reg consume_error,
 input wire word_valid,word_end,word_kind,input wire [15:0] word_generation,input wire [9:0] word_slot,input wire [5:0] word_length,
 output wire word_ready,output wire [9:0] meta_address,output wire meta_write,output wire [7:0] meta_data,input wire [7:0] meta_q,
 output wire tile_empty,
 input wire [23:0] address,input wire read_n,write_n,output wire [7:0] data_out,output wire oe_n);
 (* ramstyle="M9K" *) reg [7:0] storage[0:4095];
 reg [11:0] head,tail,used,copy_tail,ordinary_at,wanted,base;
 reg [7:0] sh,st,check_at;reg [8:0] stamps,checked_tiles,needed;
 reg filling,valid,owned_tile,binding;reg [31:0] token,stamp;
 reg [15:0] expected_generation;reg [9:0] expected_slot;reg expected_kind;
 localparam P_IDLE=0,P_READ=1,P_COPY=2,P_STAMP=3,P_RETURN=4;
 reg [2:0] ps;reg [4:0] lane;reg [1:0] stamp_lane;reg [31:0] copied_stamp;reg [5:0] copied_length;
 localparam B_IDLE=0,B_READ=1,B_CAP=2;
 reg [1:0] bs,bind_lane;
 wire live=active&&!reset&&!producer_error&&!consume_error;
 wire copy_write=live&&ps==P_COPY;
 wire ordinary_write=byte_valid&&byte_ready;
 wire prefill_commit=live&&ps==P_RETURN;
 wire take_tile=consume&&chunk_ready&&consume_token==token&&owned_tile;
 wire [8:0] consume_stamps=wanted>>(expected_kind?5:4);
 function automatic [11:0] next_byte(input [11:0] a);next_byte=a==3583?12'd0:a+1'b1;endfunction
 function automatic [7:0] next_stamp(input [7:0] a);next_stamp=a==191?8'd0:a+1'b1;endfunction
 wire [12:0] taken_head={1'b0,head}+{1'b0,wanted};
 wire [8:0] taken_stamp={1'b0,sh}+consume_stamps;
 assign begin_ready=live&&!valid&&!filling&&!binding;
 assign byte_ready=live&&filling&&!owned_tile&&ordinary_at<wanted&&!copy_write;
 assign chunk_ready=live&&valid;
 assign tile_empty=used==0&&stamps==0&&ps==P_IDLE&&!binding;
 // A returned mailbox is acknowledged only after data AND all4 stamp bytes.
 assign word_ready=live&&((word_end&&ps==P_IDLE)||ps==P_RETURN);
 wire bind_access=binding&&ps==P_IDLE;
 assign meta_address=ps==P_READ||ps==P_COPY?{5'd0,lane}:
  ps==P_STAMP?10'd32+{st,2'b00}+stamp_lane:
  bind_access?10'd32+{check_at,2'b00}+bind_lane:10'd800;
 assign meta_write=live&&ps==P_STAMP;
 assign meta_data=copied_stamp[stamp_lane*8+:8];
 always @(posedge clk)begin
  if(copy_write)storage[copy_tail]<=meta_q;
  else if(ordinary_write)storage[12'd3584+ordinary_at]<=byte_data;
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   head<=0;tail<=0;used<=0;sh<=0;st<=0;stamps<=0;copy_tail<=0;ordinary_at<=0;wanted<=0;base<=0;
   filling<=0;valid<=0;owned_tile<=0;binding<=0;token<=0;producer_error<=0;consume_error<=0;
   ps<=P_IDLE;lane<=0;stamp_lane<=0;copied_stamp<=0;copied_length<=0;bs<=B_IDLE;bind_lane<=0;stamp<=0;check_at<=0;checked_tiles<=0;needed<=0;
   expected_generation<=0;expected_slot<=0;expected_kind<=0;
  end else if(live)begin
   case({prefill_commit,take_tile})
    2'b10:begin used<=used+copied_length;stamps<=stamps+1'b1;end
    2'b01:begin used<=used-wanted;stamps<=stamps-consume_stamps;end
    2'b11:begin used<=used+copied_length-wanted;stamps<=stamps+1'b1-consume_stamps;end
    default:;
   endcase
   if(consume)begin
    if(!valid||consume_token!=token)consume_error<=1;
    else begin
     valid<=0;
     if(owned_tile)begin head<=taken_head>=3584?taken_head-3584:taken_head;sh<=taken_stamp>=192?taken_stamp-192:taken_stamp;end
    end
   end
   if(begin_valid&&begin_ready)begin
    if(begin_length==0||begin_length>(begin_tile?2048:512)||(begin_tile&&(begin_length& (kind?31:15))))producer_error<=1;
    else begin
     owned_tile<=begin_tile;wanted<=begin_length;token<=begin_token;ordinary_at<=0;
     if(begin_tile)begin
      binding<=1;bs<=B_IDLE;bind_lane<=0;checked_tiles<=0;check_at<=sh;needed<=begin_length>>(kind?5:4);
      expected_generation<=generation;expected_slot<=first;expected_kind<=kind;base<=head;
     end else begin filling<=1;base<=3584;end
    end
   end
   if(ordinary_write)ordinary_at<=ordinary_at+1'b1;
   if(seal)begin
    if(!filling||ordinary_at!=wanted)producer_error<=1;
    else begin filling<=0;valid<=1;end
   end
   case(ps)
    P_IDLE:begin
     // A binding scan already in flight owns the metadata port until done.
     if((!binding||bs==B_IDLE)&&( !binding||stamps<needed||used<wanted)&&word_valid&&!word_end&&used+word_length<=3584&&stamps<192)begin
      if(word_generation!=generation||word_length!=(word_kind?32:16))producer_error<=1;
      else begin copied_stamp<={5'd0,word_generation,word_kind,word_slot};copied_length<=word_length;copy_tail<=tail;lane<=0;ps<=P_READ;end
     end else if(binding&&bs==B_IDLE&&stamps>=needed&&used>=wanted)bs<=B_READ;
    end
    P_READ:ps<=P_COPY;
    P_COPY:begin
     copy_tail<=next_byte(copy_tail);
     if(lane==copied_length-1)begin stamp_lane<=0;ps<=P_STAMP;end
     else begin lane<=lane+1'b1;ps<=P_READ;end
    end
    P_STAMP:if(stamp_lane==3)begin tail<=copy_tail;st<=next_stamp(st);ps<=P_RETURN;end else stamp_lane<=stamp_lane+1'b1;
    P_RETURN:ps<=P_IDLE;
    default:producer_error<=1;
   endcase
   if(bind_access)case(bs)
    B_READ:bs<=B_CAP;
    B_CAP:begin
     stamp[bind_lane*8+:8]<=meta_q;
     if(bind_lane==3)begin
      if({meta_q,stamp[23:0]}!={5'd0,expected_generation,expected_kind,expected_slot})producer_error<=1;
      else if(checked_tiles+1==needed)begin binding<=0;bs<=B_IDLE;valid<=1;end
      else begin checked_tiles<=checked_tiles+1'b1;check_at<=next_stamp(check_at);expected_slot<=expected_slot+1'b1;bind_lane<=0;bs<=B_READ;end
     end else begin bind_lane<=bind_lane+1'b1;bs<=B_READ;end
    end
    default:;
   endcase
  end
 end
 // Independent synchronous read port; TILE prefill and ordinary writes use A.
 reg [23:0] am,asyn,result_address;reg [31:0] result_token;reg result_valid;reg [7:0] result_data;
 wire selected=address>=24'h400800&&address<24'h401800;
 wire [11:0] offset=asyn-24'h400800;
 wire [12:0] linear={1'b0,base}+{1'b0,offset};
 wire [11:0] physical=owned_tile?(linear>=3584?linear-3584:linear):linear[11:0];
 always @(posedge clk)begin
  am<=address;asyn<=am;result_address<=asyn;result_token<=token;
  result_valid<=chunk_ready&&asyn>=24'h400800&&asyn<24'h401800&&offset<wanted;
  result_data<=storage[physical];
 end
 assign data_out=result_data;
 assign oe_n=!(live&&!read_n&&write_n&&selected&&chunk_ready&&result_valid&&result_address==address&&result_token==token);
endmodule
