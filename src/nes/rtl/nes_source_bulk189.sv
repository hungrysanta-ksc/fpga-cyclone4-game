// SPDX-License-Identifier: MIT
// Actual native exporter records -> existing CDC mailbox -> cartridge chunks.
// Preserves1813 compact record bytes, NOT SNES-render-ready section packets.
module nes_source_bulk189(
 input wire nes_clk,host_clk,raw_reset,active,stop,
 input wire record_valid,output wire record_ready,input wire [95:0] record_data,
 input wire prepared_valid,output wire prepared_ready,
 input wire prepared_accept,input wire [15:0] prepared_generation,
 output wire ack_valid,input wire ack_ready,output wire ack_accept,output wire [15:0] ack_generation,
 // Fresh namespace supplied by the session owner, stable throughout the run.
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
 localparam INIT=0,IDLE=1,FIRST=2,WRITE=3,NEXT=4,SEAL=5;
 reg [2:0] state;
 reg [95:0] held;
 reg [3:0] position,total;
 reg [11:0] used;
 reg [31:0] token;
 reg failed;
 wire open_ready,put_ready,producer_error,consume_error;
 function automatic [3:0] width(input [2:0] kind);
  case(kind)0:width=2;1,5:width=1;2,4:width=7;3:width=4;6:width=2;default:width=8;endcase
 endfunction
 wire [3:0] next_total=width(word_data[95:93])+4'd4;
 wire room=used+{8'd0,next_total}<=2048;
 wire control_end=held[95:93]==7&&(held[76:64]==1||held[76:64]==2||held[76:64]==3);
 wire [15:0] tag={held[95:93],held[76:64]};
 reg [7:0] encoded;
 always @*case(position)
  0:encoded=tag[15:8];1:encoded=tag[7:0];2:encoded=held[92:85];3:encoded=held[84:77];
  default:encoded=held[63:0]>>((total-1-position)*8);
 endcase
 assign word_ready=!reset&&!failed&&(state==FIRST||(state==NEXT&&room));
 assign busy=state!=IDLE&&state!=INIT||word_valid||chunk_ready;
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
  if(reset)begin state<=INIT;held<=0;position<=0;total<=0;used<=0;token<=0;failed<=0;end
  else begin
   if(producer_error)failed<=1;
   if(!failed)case(state)
    INIT:begin token<=token_seed;state<=IDLE;end
    IDLE:if(word_valid&&open_ready)begin used<=0;state<=FIRST;end
    FIRST,NEXT:if(word_valid)begin
     if(state==NEXT&&!room)state<=SEAL;
     else begin held<=word_data;total<=next_total;position<=0;state<=WRITE;end
    end
    WRITE:if(put_ready)begin
     used<=used+1'b1;
     if(position==total-1)begin
      if(control_end)state<=SEAL;else state<=NEXT;
     end else position<=position+1'b1;
    end
    SEAL:begin
     // No implicit wrap: a session owner must supply a fresh namespace.
     if(token==32'hffffffff)failed<=1;else token<=token+1'b1;
     state<=IDLE;
    end
    default:state<=INIT;
   endcase
  end
 end
endmodule
