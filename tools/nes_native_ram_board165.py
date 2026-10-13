# SPDX-License-Identifier: MIT
"""Separate RAM read registers from valid/output selection, preserving latency."""
def materialize(out):
 def edit(n,fn):
  p=out/n;s=p.read_text();p.write_text(fn(s),encoding='utf8')
 def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
 def compact(s):
  s=once(s,'output reg response,hit,output reg [63:0] data','output reg response,hit,output wire [63:0] data')
  s=once(s,' always @(posedge clk)begin\n  response<=0;hit<=0;data<=0;',''' reg [14:0] map_q;reg [7:0] row_q;reg [63:0] object_q;reg [19:0] exception_q;
 reg [1:0] read_kind;
 always @(posedge clk)begin
  map_q<=maps[query_address];row_q<=rows[query_address[7:0]];
  object_q<=objects[query_address[6:0]];exception_q<=exceptions[query_address[6:0]];
  read_kind<=query_kind;
 end
 assign data=!hit?64'd0:read_kind==0?{49'd0,map_q}:read_kind==1?{56'd0,row_q}:read_kind==2?object_q:{44'd0,exception_q};
 always @(posedge clk)begin
  response<=0;hit<=0;''')
  for a in ["data<={49'd0,maps[query_address]};","data<={56'd0,rows[query_address[7:0]]};","data<=objects[query_address[6:0]];","data<={44'd0,exceptions[query_address[6:0]]};"]:s=once(s,a,'')
  return s
 def raster(s):
  s=once(s,'output reg [55:0] data','output wire [55:0] data')
  s=once(s,' always @(posedge clk) begin\n  response<=0;hit<=0;data<=0;',''' reg [55:0] row_q;reg [7:0] color_q;reg palette_q;
 always @(posedge clk)begin
  row_q<=rows[query_row];color_q<=colors[{query_bank,query_color}];palette_q<=query_palette;
 end
 assign data=!hit?56'd0:palette_q?{48'd0,color_q}:row_q;
 always @(posedge clk) begin
  response<=0;hit<=0;''')
  return once(s,"     data<=query_palette?{48'd0,colors[{query_bank,query_color}]}:rows[query_row];",'')
 def planes(s):
  s=once(s,'output reg response,output reg [1:0] required_kind','output reg response,output wire [1:0] required_kind')
  s=once(s,' reg pair_pending;',''' reg query_hit;
 // Query is accepted only while owned; capture mark occurs only while active.
 always @(posedge clk)tile_q<=required_tiles[owned?query_tile:physical_address[16:4]];
 assign required_kind=query_hit?tile_q:2'd0;
 reg pair_pending;''')
  s=once(s,'reg [1:0] pending_kind,pending_old,last_value;','reg [1:0] pending_kind,last_value,tile_q;wire [1:0] pending_old=tile_q;')
  s=once(s,'   if(mark)pending_old<=required_tiles[physical_address[16:4]];','')
  s=once(s,'event_valid<=0;response<=0;required_kind<=0;','event_valid<=0;response<=0;query_hit<=0;')
  return once(s,'if(valid)required_kind<=required_tiles[query_tile];','if(valid)query_hit<=1;')
 def spi(s):
  s=once(s,' reg [7:0] buffer[0:255];',''' (* ramstyle="M9K" *) reg [7:0] buffer[0:255];
 reg [7:0] read_byte;''')
  s=once(s,' reg [7:0] shift,command,arg,arg_not,received_crc,tail,request_crc;',' always @(posedge clk)read_byte<=buffer[byte_count-9\'d1];\n reg [7:0] shift,command,arg,arg_not,received_crc,tail,request_crc;')
  # A serial byte takes32 host clocks at this fixed speed; the read register
  # settles after byte_count advances, before the next SPI falling edge.
  return once(s,'reply=buffer[byte_count-1];','reply=read_byte;')
 edit('nes_native_compact_planes165.sv',compact)
 edit('nes_native_raster_frame165.sv',raster)
 edit('nes_native_planes165.sv',planes)
 edit('nes_native_spi165.sv',spi)
