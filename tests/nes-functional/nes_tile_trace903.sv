// 84 MHz passive observer. Latest events are drained into independent RAM
// addresses within eight clocks, well before the corresponding SPI reply byte.
module nes_tile_trace903(
 input wire clk,reset,active,writer,reader,ready,e8,kind,issue,
 input wire [31:0] checked_token,
 input wire header,retired,show,query,input wire [7:0] data,op,
 input wire [15:0] generation,input wire [4:0] index,output reg [7:0] reply);
 reg [24:0] counter;
 wire [15:0] now=counter[24:9];
 reg last_writer,last_reader,last_ready,observed,last_kind;
 wire publish=writer!=last_writer;
 wire visible=ready && (!last_ready || reader!=last_reader);
 wire sample=e8 && ready && (!observed || visible);
 reg sealed,shown,acked,had_tile;
 wire begin_frame=retired && op==1;
 wire reveal=sealed && !shown && show;
 reg [15:0] previous_show;
 wire [7:0] events={query,reveal,header && data==7,issue,sample,visible,publish,begin_frame};
 reg [7:0] pending;
 wire [2:0] slot=counter[2:0];
 (* ramstyle="M9K" *) reg [15:0] stamps[0:7];
 reg [15:0] q;
 wire [4:0] offset=index-5'd5;
 always @(posedge clk)begin
  q<=stamps[offset[3:1]];
  if(reset || !active)begin
   counter<=0;pending<=0;previous_show<=0;last_writer<=0;last_reader<=0;last_ready<=0;
   observed<=0;last_kind<=0;sealed<=0;shown<=0;acked<=0;had_tile<=0;
  end else begin
   counter<=counter+1'b1;
   last_writer<=writer;last_reader<=reader;last_ready<=ready;
   if(visible || !ready)observed<=0;
   if(sample)begin observed<=1;last_kind<=kind;end
   if(begin_frame)begin sealed<=0;shown<=0;acked<=0;had_tile<=0;end
   if(header && data==7)had_tile<=1;
   if(header && data==3)sealed<=1;
   if(reveal)begin previous_show<=now;shown<=1;end
   if(retired && op==3 && shown)acked<=1;
   pending<=(pending|events) & ~(8'b1<<slot);
   if(pending[slot] || events[slot])stamps[slot]<=slot==0 ? previous_show : now;
  end
 end
 always @* case(index)
  1:reply=8'h93;
  2:reply={5'b0,had_tile,shown,acked};
  3:reply=generation[7:0];4:reply=generation[15:8];
  21:reply=checked_token[7:0];22:reply=checked_token[15:8];
  23:reply=checked_token[23:16];24:reply=checked_token[31:24];
  25:reply={7'b0,last_kind};
  default:reply=offset[0]?q[15:8]:q[7:0];
 endcase
endmodule
