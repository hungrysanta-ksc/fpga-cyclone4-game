// SPDX-License-Identifier: MIT
//046 streaming restricted BG fetch encoder. Physical PPU tap/mode monitor excluded.
module nes_ncr1_encoder(
 input wire queue_clk,reset,
 input wire [15:0] reset_epoch,
 input wire frame_start,frame_end,supported_mode,
 input wire [7:0] frame_id,
 input wire [2:0] fine_x,
 input wire chr_32k,
 input wire [63:0] palette_snes,
 input wire bg_valid,
 input wire signed [8:0] bg_line,
 input wire [8:0] bg_dot,
 input wire [14:0] bg_chr_address,
 input wire [1:0] bg_palette,
 input wire [31:0] bg_tick,
 output wire frame_ready,
 output reg encoder_fault,
 output reg [7:0] encoder_error,
 output wire desc_valid,
 input wire desc_ready,
 output reg [15:0] desc_epoch,desc_seq,
 output wire [23:0] desc_base,
 output wire [11:0] desc_length,
 input wire done,
 input wire mem_req_valid,
 output wire mem_req_ready,
 input wire [23:0] mem_req_address,
 input wire [15:0] mem_req_epoch,
 output wire mem_rsp_valid,
 input wire mem_rsp_ready,
 output reg [23:0] mem_rsp_address,
 output reg [15:0] mem_rsp_epoch,
 output reg [7:0] mem_rsp_data,
 output reg mem_rsp_error
);
 reg active,complete,sent,exhausted,window_valid,window_q;
 reg [7:0] frame_q;reg [2:0] fine_q;reg chr32_q;reg [63:0] palette_q;
 reg signed [8:0] expected_line;
 reg [6:0] slot;
 reg [14:0] raw_count,useful_count;
 reg [31:0] previous_tick,release_tick;
 wire [5:0] fetch_tile=slot[6:1];
 wire [8:0] expected_dot=fetch_tile<32 ? {fetch_tile,3'b0}+9'd5+{7'b0,slot[0],1'b0} :
                          fetch_tile==32 ? 9'd325+{7'b0,slot[0],1'b0} : 9'd333+{7'b0,slot[0],1'b0};
 wire cadence_ok=bg_line==expected_line && bg_dot==expected_dot && raw_count<16388;
 wire main_fetch=bg_line>=0 && bg_line<240 && bg_dot<=247;
 wire pre_fetch=bg_line>=-1 && bg_line<239 && bg_dot>=321;
 wire relevant=main_fetch || pre_fetch;
 wire [7:0] y=main_fetch ? bg_line[7:0] : bg_line[7:0]+8'd1;
 wire [8:0] pre_offset=bg_dot-9'd321;
 wire [5:0] x=main_fetch ? {1'b0,bg_dot[7:3]}+6'd2 : pre_offset[8:3];
 wire [9:0] cell_address=({5'b0,y[7:3]}<<5)+{5'b0,y[7:3]}+{4'b0,x};
 wire event_ok=active && !encoder_fault && supported_mode && bg_valid && cadence_ok &&
               (raw_count==0 || bg_tick>previous_tick);
 wire first_row_plane=(y[2:0]==0 && !slot[0]);
 wire cell_write=event_ok && relevant && first_row_plane;
 (* ramstyle="M9K" *) reg [10:0] cells[0:989];
 reg [10:0] tile_q;
 reg check_pending,check_first;reg [10:0] check_tile;
 reg rsp_pending,rsp_valid_q;reg [11:0] request_address;
 wire request_fire=mem_req_valid && mem_req_ready;
 wire [11:0] map_offset=mem_req_address[11:0]-12'd20;
 wire [11:0] edge_offset=mem_req_address[11:0]-12'd1940;
 wire [9:0] map_word=map_offset[10:1];
 wire [4:0] edge_row=edge_offset[5:1];
 wire [9:0] packet_cell=mem_req_address<1940 ? map_word+{5'b0,map_word[9:5]} :
                           ({5'b0,edge_row}<<5)+{5'b0,edge_row}+10'd32;
 wire packet_ram_read=request_fire && mem_req_address>=20 && mem_req_address<2000;
 // Capture and ownership phases are disjoint. One physical RAM read/write port;
 // first-row writes do not need old-data reads, avoiding read-during-write reliance.
 wire tile_read=packet_ram_read || (event_ok && relevant && !first_row_plane);
 wire [9:0] tile_address=packet_ram_read ? packet_cell : cell_address;
 always @(posedge queue_clk)begin
  if(cell_write)cells[tile_address]<=bg_chr_address[14:4];
  else if(tile_read)tile_q<=cells[tile_address];
 end
 assign frame_ready=!reset && !encoder_fault && !active && !complete && !exhausted;
 assign desc_valid=!reset && !encoder_fault && complete && !sent;
 assign desc_base=24'd0;assign desc_length=12'd2008;
 assign mem_req_ready=!reset && !encoder_fault && complete && sent && !rsp_pending && !rsp_valid_q;
 assign mem_rsp_valid=!reset && !encoder_fault && rsp_valid_q;
 function automatic [7:0] packet_byte(input [11:0] a,input [10:0] tile,
  input [7:0] id,input [2:0] fx,input win,input [31:0] tick,input [63:0] pal);
  case(a)
   0:packet_byte="N";1:packet_byte="C";2:packet_byte="R";3:packet_byte="1";
   4:packet_byte=1;5:packet_byte=id;6:packet_byte={5'b0,fx};7:packet_byte={7'b0,win};
   8:packet_byte=0;9:packet_byte=1;10:packet_byte=240;11:packet_byte=0;
   12:packet_byte=tick[7:0];13:packet_byte=tick[15:8];
   14:packet_byte=tick[23:16];15:packet_byte=tick[31:24];
   16:packet_byte=8'hbc;17:packet_byte=7;18:packet_byte=0;19:packet_byte=0;
   default:if(a<2000)packet_byte=a[0] ? {6'b0,tile[9:8]} : tile[7:0];
           else if(a<2008)packet_byte=pal[(a-2000)*8+:8];
           else packet_byte=0;
  endcase
 endfunction
 task automatic fail(input [7:0] code);
  begin encoder_fault<=1;encoder_error<=code;active<=0;complete<=0;end
 endtask
 always @(posedge queue_clk)begin
  if(reset)begin
   desc_epoch<=reset_epoch;desc_seq<=1;encoder_fault<=0;encoder_error<=0;
   active<=0;complete<=0;sent<=0;exhausted<=0;window_valid<=0;window_q<=0;
   frame_q<=0;fine_q<=0;chr32_q<=0;palette_q<=0;expected_line<=-9'sd1;slot<=0;
   raw_count<=0;useful_count<=0;previous_tick<=0;release_tick<=0;
   check_pending<=0;check_first<=0;check_tile<=0;rsp_pending<=0;rsp_valid_q<=0;
   request_address<=0;mem_rsp_address<=0;mem_rsp_epoch<=0;mem_rsp_data<=0;mem_rsp_error<=0;
  end else if(!encoder_fault)begin
   check_pending<=0;
   if(mem_rsp_valid && mem_rsp_ready)rsp_valid_q<=0;
   if(request_fire)begin
    rsp_pending<=1;request_address<=mem_req_address[11:0];
    mem_rsp_address<=mem_req_address;mem_rsp_epoch<=mem_req_epoch;
    mem_rsp_error<=mem_req_epoch!=desc_epoch || mem_req_address>=2008;
   end
   if(rsp_pending)begin rsp_pending<=0;rsp_valid_q<=1;mem_rsp_data<=packet_byte(request_address,tile_q,frame_q,fine_q,window_q,release_tick,palette_q);end
   if(desc_valid && desc_ready)sent<=1;
   if(done)begin
    if(!complete || !sent)fail(8'h0a);
    else begin complete<=0;sent<=0;if(desc_seq==65535)exhausted<=1;else desc_seq<=desc_seq+1'b1;end
   end
   if(frame_start)begin
    if(!frame_ready || bg_valid || frame_end)fail(8'h01);
    else if(!supported_mode || frame_id<1 || frame_id>4)fail(8'h02);
    else begin
     active<=1;frame_q<=frame_id;fine_q<=fine_x;chr32_q<=chr_32k;palette_q<=palette_snes;
     raw_count<=0;useful_count<=0;expected_line<=-9'sd1;slot<=0;
     window_valid<=0;previous_tick<=0;release_tick<=0;
    end
   end
   if(active && !supported_mode)fail(8'h02);
   if(bg_valid)begin
    if(!active || frame_end || frame_start)fail(8'h0b);
    else if(!cadence_ok)fail(8'h03);
    else if(raw_count!=0 && bg_tick<=previous_tick)fail(8'h04);
    else begin
     raw_count<=raw_count+1'b1;previous_tick<=bg_tick;
     if(slot==67)begin slot<=0;expected_line<=expected_line+1'b1;end else slot<=slot+1'b1;
     if(relevant)begin
      if(bg_chr_address[2:0]!=y[2:0] || bg_chr_address[3]!=slot[0] || (!chr32_q && bg_chr_address[14]))fail(8'h05);
      else if(bg_palette!=0)fail(8'h06);
      else if(window_valid && bg_chr_address[14]!=window_q)fail(8'h08);
      else begin
       window_valid<=1;window_q<=bg_chr_address[14];release_tick<=bg_tick;useful_count<=useful_count+1'b1;
       check_pending<=1;check_first<=first_row_plane;check_tile<=bg_chr_address[14:4];
      end
     end
    end
   end
   if(check_pending && !check_first && tile_q!=check_tile)fail(8'h07);
   if(frame_end)begin
    if(!active || bg_valid || check_pending || raw_count!=16388 || useful_count!=15840)fail(8'h09);
    else begin active<=0;complete<=1;sent<=0;end
   end
  end
 end
endmodule
