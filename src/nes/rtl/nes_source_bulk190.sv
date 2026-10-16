// SPDX-License-Identifier: MIT
// 1901 transport: one checked 16-byte NES CHR tile per 22-byte record.
// Native NES planes remain unchanged. Not final SNES graphics/slot allocation.
module nes_source_bulk190(
 input wire nes_clk,host_clk,raw_reset,active,stop,
 input wire record_valid,output wire record_ready,input wire [95:0] record_data,
 input wire prepared_valid,output wire prepared_ready,
 input wire prepared_accept,input wire [15:0] prepared_generation,
 output wire ack_valid,input wire ack_ready,output wire ack_accept,output wire [15:0] ack_generation,
 input wire [31:0] token_seed,
 output wire chunk_ready,output wire [11:0] chunk_length,output wire [31:0] chunk_token,
 input wire consume,input wire [31:0] consume_token,
 input wire [23:0] address,input wire read_n,write_n,
 output wire [7:0] data_out,output wire oe_n,dir,
 output wire busy,output wire fault
);
 wire common_reset=raw_reset||!active||stop;
 wire reset;
 nes_domain_reset124 local_release(.clk(host_clk),.raw_reset(common_reset),.reset(reset));
 wire word_valid,word_ready;wire [95:0] word_data;wire [16:0] ack_data;
 nes_native_mailbox165 records(.src_clk(nes_clk),.dst_clk(host_clk),.reset(common_reset),
  .src_valid(record_valid),.src_ready(record_ready),.src_data(record_data),
  .dst_valid(word_valid),.dst_ready(word_ready),.dst_data(word_data));
 nes_native_mailbox165 #(.WIDTH(17)) prepared(.src_clk(host_clk),.dst_clk(nes_clk),.reset(common_reset),
  .src_valid(prepared_valid),.src_ready(prepared_ready),.src_data({prepared_accept,prepared_generation}),
  .dst_valid(ack_valid),.dst_ready(ack_ready),.dst_data(ack_data));
 assign {ack_accept,ack_generation}=ack_data;
 localparam INIT=0,IDLE=1,FIRST=2,WRITE=3,NEXT=4,SEAL=5,GATHER=6;
 reg [2:0] state;
 reg [95:0] held;
 reg [4:0] position,total;
 reg [3:0] next_lane;
 reg [7:0] tile_data[0:15]; // Written completely before exposure; no reset mux.
 reg [11:0] used;
 reg [31:0] token;
 reg failed;
 wire open_ready,put_ready,producer_error,consume_error;
 function automatic [4:0] width(input [2:0] kind);
  case(kind)0:width=2;1,5:width=1;2,4:width=7;3:width=4;6:width=18;default:width=8;endcase
 endfunction
 wire [4:0] next_total=width(word_data[95:93])+5'd4;
 wire room=used+{7'd0,next_total}<=2048;
 wire control_end=held[95:93]==7&&(held[76:64]==1||held[76:64]==2||held[76:64]==3);
 wire incoming_abort=word_data[95:93]==7&&word_data[76:64]==2;
 wire tile_byte_ok=word_data[95:93]==6&&word_data[63:14]==0&&word_data[13:12]!=0;
 wire [15:0] tag={held[95:93],held[76:64]};
 reg [7:0] encoded;
 always @*case(position)
  0:encoded=tag[15:8];1:encoded=tag[7:0];2:encoded=held[92:85];3:encoded=held[84:77];
  default:begin
   if(held[95:93]==6)begin
    if(position==4)encoded={6'd0,held[13:12]};
    else if(position==5)encoded=0; // layout0: NES plane0[8],plane1[8].
    else encoded=tile_data[position-6];
   end else encoded=held[63:0]>>((total-1-position)*8);
  end
 endcase
 assign word_ready=!reset&&!failed&&(state==FIRST||state==GATHER||(state==NEXT&&room));
 assign busy=(state!=IDLE&&state!=INIT)||word_valid||chunk_ready;
 assign fault=failed||producer_error||consume_error;
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(
  .clk(host_clk),.reset(raw_reset),.active(active),.stop(stop),
  .begin_valid(state==IDLE&&word_valid&&!failed),.begin_length(12'd2048),.begin_token(token),.begin_ready(open_ready),
  .byte_valid(state==WRITE&&!failed),.byte_data(encoded),.byte_ready(put_ready),
  .seal(state==SEAL&&!failed),.cancel(1'b0),.producer_error(producer_error),
  .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),
  .consume(consume),.consume_token(consume_token),.consume_error(consume_error),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(data_out),.oe_n(oe_n),.dir(dir));
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin state<=INIT;held<=0;position<=0;total<=0;next_lane<=0;used<=0;token<=0;failed<=0;end
  else begin
   if(producer_error)failed<=1;
   if(!failed)case(state)
    INIT:begin token<=token_seed;state<=IDLE;end
    IDLE:if(word_valid&&open_ready)begin used<=0;state<=FIRST;end
    FIRST,NEXT:if(word_valid)begin
     if(state==NEXT&&!room)state<=SEAL;
     else begin
      held<=word_data;total<=next_total;position<=0;
      if(word_data[95:93]==6)begin
       if(!tile_byte_ok||word_data[11:8]!=0)failed<=1;
       else begin tile_data[0]<=word_data[7:0];next_lane<=1;state<=GATHER;end
      end else begin
       if(word_data[95:93]==7&&word_data[76:64]==0)begin
        if(word_data[63:48]!=16'h1813)failed<=1;
        held[63:48]<=16'h1901;
       end
       state<=WRITE;
      end
     end
    end
    GATHER:if(word_valid)begin
     if(incoming_abort&&word_data[92:77]==held[92:77])begin
      // No tile bytes have been written. Preserve source ABORT, discard fragment.
      held<=word_data;total<=12;position<=0;state<=WRITE;
     end else if(!tile_byte_ok||word_data[92:64]!=held[92:64]||
                 word_data[13:12]!=held[13:12]||word_data[11:8]!=next_lane)failed<=1;
     else begin
      tile_data[next_lane]<=word_data[7:0];
      if(next_lane==15)state<=WRITE;else next_lane<=next_lane+1'b1;
     end
    end
    WRITE:if(put_ready)begin
     used<=used+1'b1;
     if(position==total-1)begin
      if(control_end)state<=SEAL;else state<=NEXT;
     end else position<=position+1'b1;
    end
    SEAL:begin
     if(token==32'hffffffff)failed<=1;else token<=token+1'b1;
     state<=IDLE;
    end
    default:state<=INIT;
   endcase
  end
 end
endmodule
