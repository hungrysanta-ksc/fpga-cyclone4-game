// Passive 84 MHz diagnostic. The ARM reads one complete record after final E0.
module nes_display1010(input wire clk,reset,active,cancel,first_e9,writer,returned,
 input wire tile_done,input wire [31:0] token,input wire [15:0] generation,
 input wire header,input wire [7:0] data,input wire retired,input wire [7:0] op,
 input wire dma,show,query,input wire [4:0] index,output reg [7:0] reply);

 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] done_sync;
 reg done_previous,writer_previous;
 reg clear_record;
 reg [30:0] clock_count;
 wire [15:0] now=clock_count[30:15];
 reg [9:0] origin,published,anchor;
 reg [7:0] tiles,chunks;
 reg live,prev_valid,sealed,has_dma,shown,complete,bad,read_ok;
 reg [15:0] previous_show;
 wire begin_frame=retired && op==1;
 wire seal_event=live && header && data==3 && !sealed;
 wire dma_event=live && !shown && dma;
 wire show_event=live && sealed && !shown && show;
 wire ack_event=live && retired && op==3;
 wire [4:0] events={ack_event,show_event,dma_event,seal_event,begin_frame};
 wire wrap=&clock_count;
 // A double event cannot occupy one RAM write port. Never publish such a row.
 wire multiple=(begin_frame && |events[4:1]) || (seal_event && |events[4:2]) ||
               (dma_event && |events[4:3]) || (show_event && ack_event);
 wire [2:0] write_slot=ack_event?4:show_event?3:dma_event?2:seal_event?1:0;
 (* ramstyle="M9K" *) reg [15:0] stamps[0:7];
 reg [15:0] q;
 always @(posedge clk) begin
  if(|events) stamps[write_slot]<=begin_frame?previous_show:now;
  q<=stamps[index[3:1]];
  done_sync<={done_sync[0],tile_done};
  done_previous<=done_sync[1];
  writer_previous<=writer;
  clock_count<=clock_count+1'b1;
  clear_record<=reset || !active || cancel;
  if(clear_record) begin
   clock_count<=0;live<=0;prev_valid<=0;sealed<=0;has_dma<=0;shown<=0;complete<=0;
   bad<=1;read_ok<=0;tiles<=0;chunks<=0;anchor<=0;published<=0;origin<=0;
  end else begin
   if(first_e9) begin origin<=now[9:0];tiles<=0;chunks<=0;end
   else begin
    if(done_sync[1] && !done_previous && !(&tiles)) tiles<=tiles+1'b1;
    if(returned && !(&chunks)) chunks<=chunks+1'b1;
   end
   if(writer!=writer_previous) published<=now[9:0];
   if(complete && (first_e9 || returned || writer!=writer_previous || header ||
                   retired || (done_sync[1] && !done_previous))) complete<=0;
   if(begin_frame) begin
    live<=1;sealed<=0;has_dma<=0;shown<=0;complete<=0;bad<=!prev_valid;prev_valid<=0;
   end
   if(seal_event) sealed<=1;
   if(dma_event) has_dma<=1;
   if(show_event) begin shown<=1;previous_show<=now;prev_valid<=1;end
   if(ack_event) begin complete<=shown && sealed && has_dma;live<=0;end
   if(multiple || wrap) bad<=1;
   if(wrap) prev_valid<=0;
   if(query) begin anchor<=now[9:0];read_ok<=complete && !bad;end
   if(first_e9 || returned || writer!=writer_previous || header || retired || (done_sync[1] && !done_previous)
      || |events || wrap) read_ok<=0;
  end
 end

 always @(posedge clk) case(index)
  1:reply<=8'ha1;
  2:reply<=generation[7:0];3:reply<=generation[15:8];
  4:reply<=tiles;5:reply<=chunks;
  6:reply<=origin[7:0];7:reply<={6'b0,origin[9:8]};
  8:reply<=anchor[7:0];9:reply<={6'b0,anchor[9:8]};
  10:reply<=published[7:0];11:reply<={6'b0,published[9:8]};
  12:reply<=token[7:0];13:reply<=token[15:8];14:reply<=token[23:16];15:reply<=token[31:24];
  16,18,20,22,24:reply<=q[7:0];
  17,19,21,23,25:reply<=q[15:8];
  30:reply<={3'b0,bad,complete,shown,has_dma,sealed};
  // A sampled session cancellation revokes the footer before its next serialization.
  31:reply<=(read_ok && !clear_record)?8'ha5:8'h00;
  default:reply<=0;
 endcase
endmodule
