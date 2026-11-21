// Passive host-domain observation. Timestamp units are 512 cycles at 84 MHz.
module nes_frame900(input wire clk,reset,active,header,section,
 input wire [7:0] data,input wire retired,input wire [7:0] op,
 input wire [15:0] generation,input wire dma,show,query,
 input wire [4:0] index,output reg [7:0] reply);
 reg [24:0] counter;
 wire [15:0] now=counter[24:9];
 reg [15:0] previous;
 reg [7:0] flags;
 reg map_head,tile_head,bulk,live,collision;
 wire begin_frame=retired && op==1;
 wire map_read=section && data==2;
 wire tile_read=section && bulk;
 wire seal=header && data==3 && !flags[2];
 wire final_ack=retired && op==3;
 // Map/tile head reads and independently retired packets have separate slots.
 // PPU writes and queue head reads use different SNES bus cycles.
 wire [9:0] events={query,retired&&tile_head,retired&&map_head,begin_frame,final_ack,
                     show&&flags[2]&&!flags[4],dma&&!flags[4],seal,tile_read,map_read};
 reg [3:0] addr;
 always @* casez(events)
  10'b1?????????:addr=9;
  10'b01????????:addr=8;
  10'b001???????:addr=7;
  10'b0001??????:addr=6;
  10'b00001?????:addr=5;
  10'b000001????:addr=4;
  10'b0000001???:addr=3;
  10'b00000001??:addr=2;
  10'b000000001?:addr=1;
  default:addr=0;
 endcase
 (* ramstyle="M9K" *) reg [15:0] stamp[0:15];
 reg [15:0] q;
 wire [4:0] offset=index-5'd5;
 always @(posedge clk)begin
  q<=stamp[offset[4:1]];
  if(active&&!reset && (live||begin_frame) && |events)
    stamp[addr]<=begin_frame ? previous : now;
  if(reset || !active)begin
   counter<=0;previous<=0;flags<=0;map_head<=0;tile_head<=0;bulk<=0;live<=0;collision<=0;
  end else begin
   counter<=counter+1'b1;
   if(header)begin bulk<=data==7;map_head<=0;tile_head<=0;end
   if(section)begin map_head<=map_read;tile_head<=tile_read;end
   if(begin_frame)begin flags<=0;live<=1;collision<=0;end
   else if(live)begin
    if((|events[9:5]) && (|events[4:0]) || query && (|events[8:5]))collision<=1;
    if(map_read)flags[0]<=1;
    if(tile_read)flags[1]<=1;
    if(seal)flags[2]<=1;
    if(dma && !flags[4])flags[3]<=1;
    if(events[4])begin flags[4]<=1;previous<=now;end
    if(final_ack)flags[5]<=1;
    if(events[7])flags[6]<=1;
    if(events[8])flags[7]<=1;
   end
  end
 end
 always @* case(index)
  1:reply=8'h90;
  2:reply=flags;
  3:reply=generation[7:0];
  4:reply=generation[15:8];
  25:reply={7'd0,collision};
  default:reply=offset[0]?q[15:8]:q[7:0];
 endcase
endmodule
