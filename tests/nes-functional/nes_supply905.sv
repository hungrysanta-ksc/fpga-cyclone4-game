// Passive host-clock timeline. Source event levels are registered at the NES edge
// and held for one NES clock (at least three 84 MHz observer edges).
module nes_supply905(input wire clk,reset,active,first_e9,writer,reader,returned,kind,
 input wire [7:0] units,input wire [2:0] nes_events,
 input wire [31:0] token,input wire [15:0] generation,
 input wire query,set_page,input wire [7:0] page_in,input wire [4:0] index,
 output reg [7:0] reply);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [2:0] meta,sync;
 reg [2:0] prior;
 always @(posedge clk)begin meta<=nes_events;sync<=meta;prior<=sync;end
 wire [2:0] edge_in=sync & ~prior; // done, granted, requested
 reg [24:0] counter;
 wire [9:0] now=counter[24:15]; // 390.095 us, wraps at 399.46 ms
 reg [9:0] origin,anchor,published;
 reg [9:0] first_request,first_grant,last_grant;
 reg saw_request;
 reg [5:0] grants;
 reg [7:0] tiles,page;
 reg [5:0] chunks;
 reg previous_writer;
 (* ramstyle="M9K" *) reg [35:0] tile_log[0:255];
 (* ramstyle="M9K" *) reg [31:0] chunk_log[0:63];
 reg [35:0] tile_q;
 reg [31:0] chunk_q;
 // Pages carry two entries, little endian, in byte lanes 16..31.
 always @(posedge clk)begin
  tile_q<=tile_log[{page[6:0],index[3]}];
  chunk_q<=chunk_log[{page[4:0],index[3]}];
  if(edge_in[2])tile_log[tiles]<={grants,last_grant,first_grant,first_request};
  if(returned)chunk_log[chunks]<={token[10:0],reader,kind,units,1'b0,now};
 end
 always @(posedge clk)begin
  if(reset || !active)begin
   counter<=0;tiles<=0;chunks<=0;grants<=0;previous_writer<=0;
   origin<=0;anchor<=0;published<=0;page<=0;saw_request<=0;
  end else begin
   counter<=counter+1'b1;
   previous_writer<=writer;
   if(writer!=previous_writer)published<=now;
   if(query)anchor<=now;
   if(set_page)page<=page_in;
   if(first_e9)begin origin<=now;tiles<=0;chunks<=0;grants<=0;saw_request<=0;end
   else begin
    // A same-edge request and grant can resolve on either synchronizer first.
    if((edge_in[0] || edge_in[1]) && !saw_request)begin first_request<=now;saw_request<=1;end
    if(edge_in[1])begin
     if(grants==0)first_grant<=now;
     last_grant<=now;grants<=grants+1'b1;
    end
    if(edge_in[2])begin grants<=0;saw_request<=0;if(!(&tiles))tiles<=tiles+1'b1;end
    if(returned && !(&chunks))chunks<=chunks+1'b1;
   end
  end
 end
 wire [35:0] record=page[7]?{4'd0,chunk_q}:tile_q;
 always @(posedge clk) case(index)
  1:reply=8'h95;
  2:reply=generation[7:0];3:reply=generation[15:8];
  4:reply=tiles;5:reply={2'b0,chunks};
  6:reply=origin[7:0];7:reply={6'b0,origin[9:8]};
  8:reply=anchor[7:0];9:reply={6'b0,anchor[9:8]};
  10:reply=published[7:0];11:reply={6'b0,published[9:8]};
  12:reply=token[7:0];13:reply=token[15:8];14:reply=token[23:16];15:reply=token[31:24];
  default:case(index[2:0])
   0:reply=record[7:0];1:reply=record[15:8];2:reply=record[23:16];
   3:reply=record[31:24];4:reply={4'b0,record[35:32]};default:reply=0;
  endcase
 endcase
endmodule
