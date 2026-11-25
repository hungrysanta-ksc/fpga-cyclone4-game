// Passive NES-domain log. Host SPI reads only after the checked display ACK.
module nes_supply1016(input wire clk, stop, origin_toggle, start_tile, done,
 input wire [12:0] tag,input wire [1:0] kind,input wire [15:0] generation,
 input wire accept_read,reply,capture_hit,row_hit,foreground,grant,spec_busy,demand,
 input wire [16:0] address,input wire host_clk,input wire [8:0] rd,
 input wire bank_we,input wire [31:0] bank_word,output reg [31:0] q);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] origin_sync;
 reg prior;
 always @(posedge clk)begin origin_sync<={origin_sync[0],origin_toggle};prior<=origin_sync[1];end
 wire origin=prior!=origin_sync[1];
 reg [22:0] timer;
 wire [7:0] stamp=timer[21:14];
 reg [8:0] cursor;
 reg last_foreground,last_overlap,pending_generation,bad;
 wire overlapping=demand&&spec_busy;
 wire [3:0] flags={foreground&&!last_foreground,grant,overlapping&&!last_overlap,!overlapping&&last_overlap};
 wire stage=|flags;
 wire timing_event=start_tile||done||reply||stage||pending_generation;
 wire collision=((start_tile||done)&&(reply||stage))||
                (pending_generation&&(reply||stage||start_tile||done));
 wire invalid=bad||stop||collision||(timing_event&&(timer[22]||cursor==507));
 // Standalone transitions and simultaneous response flags use the same clock.
 wire [1:0] source=capture_hit?2'd0:(row_hit?2'd1:2'd2);
 wire [31:0] word=invalid?32'hfe000000:
   reply?{1'b0,source,flags,address,stamp}:
   stage?{4'h8,16'd0,flags,stamp}:
   pending_generation?{16'hd000,generation}:
   start_tile?{4'ha,done,4'b0,kind,tag,stamp}:
   done?{24'hb00000,stamp}:32'hff000000;
 (* ramstyle="M9K, no_rw_check" *) reg [31:0] records[0:511];
 reg need_sentinel;
 always @(posedge clk)begin
  if(timing_event||need_sentinel||(stop&&!bad))records[cursor]<=word;
  need_sentinel<=timing_event||origin;
 end
 // The host owns words 508..510 exclusively. The source cursor stops at 507.
 always @(posedge host_clk)begin
  if(bank_we)records[rd]<=bank_word;
  q<=records[rd];
 end
 always @(posedge clk)begin
  if(!timer[22])timer<=timer+1'b1;
  last_foreground<=foreground;
  last_overlap<=overlapping;
  pending_generation<=start_tile;
  if(timing_event&&!invalid)cursor<=cursor+1'b1;
  if(invalid)bad<=1;
  if(origin)begin timer<=0;cursor<=0;bad<=0;last_foreground<=0;last_overlap<=0;pending_generation<=0;end
  if(stop)begin bad<=1;last_foreground<=0;last_overlap<=0;pending_generation<=0;end
 end
endmodule
