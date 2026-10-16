// SPDX-License-Identifier: MIT
// Host-domain descriptor view for193. Only token consume changes ownership.
// 00:6040 ready,6041 kind,6042 length16,6044 byte offset16,6046 generation16,
// 6048 token32; writes604c..604f token then6050=A5 commits.
// Common cancellation with193 is mandatory; control consume is NOT displayACK.
module nes_bulk_control194(
 input wire clk,reset,active,stop,fault,
 input wire chunk_ready,chunk_kind,input wire [11:0] chunk_length,
 input wire [9:0] chunk_slot,input wire [15:0] chunk_generation,
 input wire [31:0] chunk_token,
 input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
 output reg [7:0] data_out,output wire oe_n,dir,
 output reg consume,output reg [31:0] consume_token,output reg command_error
);
 wire local_reset;
 nes_domain_reset124 release_local(.clk(clk),.raw_reset(reset||stop||!active||fault),.reset(local_reset));
 wire enabled=active&&!reset&&!stop&&!fault&&!local_reset;
 wire selected=address>=24'h006040&&address<=24'h006050;
 wire rd=enabled&&selected&&!read_n&&write_n;
 wire wr=enabled&&selected&&read_n&&!write_n;
 assign dir=rd;assign oe_n=!(rd||wr);
 wire [15:0] offset=chunk_kind?{1'b0,chunk_slot,5'b0}:{2'b0,chunk_slot,4'b0};
 always @* begin
  data_out=0;
  if(chunk_ready)case(address[4:0])
   0:data_out=1;1:data_out={7'd0,chunk_kind};
   2:data_out=chunk_length[7:0];3:data_out={4'd0,chunk_length[11:8]};
   4:data_out=offset[7:0];5:data_out=offset[15:8];
   6:data_out=chunk_generation[7:0];7:data_out=chunk_generation[15:8];
   8:data_out=chunk_token[7:0];9:data_out=chunk_token[15:8];
   10:data_out=chunk_token[23:16];11:data_out=chunk_token[31:24];
   default:data_out=0;
  endcase
 end
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [23:0] am,asyn;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [7:0] dm,ds;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg wm,ws,rm,rs;
 reg [23:0] ap;reg [7:0] dp;reg wp,rp;
 reg [31:0] staged;reg [3:0] mask;
 always @(posedge clk or posedge local_reset)begin
  if(local_reset)begin
   am<=0;asyn<=0;ap<=0;dm<=0;ds<=0;dp<=0;wm<=1;ws<=1;wp<=1;rm<=1;rs<=1;rp<=1;
   staged<=0;mask<=0;consume<=0;consume_token<=0;command_error<=0;
  end else begin
   am<=address;asyn<=am;ap<=asyn;dm<=data_in;ds<=dm;dp<=ds;
   wm<=write_n;ws<=wm;wp<=ws;rm<=read_n;rs<=rm;rp<=rs;
   consume<=0;command_error<=0;
   if(enabled&&ws&&!wp&&rp)begin
    if(ap>=24'h00604c&&ap<=24'h00604f)begin
     staged[ap[1:0]*8+:8]<=dp;mask[ap[1:0]]<=1;
    end
    if(ap==24'h006050)begin
     mask<=0;
     if(dp==8'ha5&&mask==15&&chunk_ready&&staged==chunk_token)begin
      consume<=1;consume_token<=staged;
     end else command_error<=1;
    end
   end
  end
 end
endmodule
