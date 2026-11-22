// SPDX-License-Identifier: MIT
// Read compact descriptors only while the sealed E9 bank is owned in NES.
// The ordinary decoder has absolute priority on the synchronous payload port.
module nes_e9_scan914(
 input wire clk, cancel, owned, port_free, input wire [9:0] length,
 input wire [15:0] generation, input wire [7:0] data,
 output wire read_req, output reg [8:0] address,
 output reg hint, output reg [12:0] tag, output reg [7:0] mask,
 input wire hint_ready
);
 reg pending, finished, matching, obj;
 reg [2:0] at, last_byte;
 assign read_req=owned&&!cancel&&!finished&&!pending&&!hint&&port_free;
 always @(posedge clk)begin
  if(cancel||!owned)begin
   address<=0;at<=0;pending<=0;finished<=0;hint<=0;
  end else begin
   if(hint&&hint_ready)hint<=0;
   if(read_req)pending<=1;
   if(pending)begin
    pending<=0;
    if(at==0)begin
     obj<=data==8'h81;
     matching<=1;
     case(data)
      8'h80:last_byte<=6;
      8'h81:last_byte<=7;
      8'h82:last_byte<=2;
      default:finished<=1; // END or a full/unsupported record
     endcase
    end else case(at)
     1:matching<=matching&&data==generation[7:0];
     2:matching<=matching&&data==generation[15:8];
     3:matching<=matching&&!data[7];
     4:matching<=matching&&data==0;
     5:tag[7:0]<=data;
     6:begin tag[12:8]<=data[4:0];matching<=matching&&data[7:5]==0;end
     7:begin mask<=data;hint<=obj&&matching&&data!=0;end
    endcase
    if(at!=0&&at==last_byte)at<=0;else at<=at+1'b1;
    if({1'b0,address}+10'd1>=length)finished<=1;
    address<=address+1'b1;
   end
  end
 end
endmodule
