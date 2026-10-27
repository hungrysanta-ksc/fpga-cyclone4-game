# SPDX-License-Identifier: MIT
"""Actual396 publication frontier and bounded prestaging. No baseline fallback."""
from nes_delta231 import ROOT,once
import nes_jobs394 as old

def arm(d):
 old.arm(d)
 p=d/'nes_refill267.c';s=p.read_text();s=s.replace('unsigned wait_armed284;','unsigned wait_armed284;\nunsigned published396,accounted396;')
 s=once(s,'static int work302(void){','static int work302(void){\n if(published396>=accounted396+33)return 1;')
 s=once(s,'  wire267[0]=0xe9;', '  if(published396+count>accounted396+33)break;\n  published396+=count; /* reserve before publication; ambiguous failure is terminal */\n  wire267[0]=0xe9;')
 p.write_text(s,newline='\n')
 p=d/'nes_bind287.c';s=p.read_text();s=s.replace('unsigned prefill_active287;','unsigned prefill_active287;\nextern unsigned published396,accounted396;')
 s=once(s,'void seed287(unsigned generation){','void seed287(unsigned generation){\n published396=accounted396=0;');p.write_text(s,newline='\n')
 p=d/'nes_native289.c';s=p.read_text();s=s.replace('unsigned tiles290(unsigned final){','extern unsigned accounted396;\nunsigned tiles290(unsigned final){')
 s=once(s,'  at290+=n;left330--;steps++;','  at290+=n;left330--;steps++;accounted396++;');p.write_text(s,newline='\n')

def rtl(d):
 old.rtl(d)
 p=d/'nes_tile_link394.sv';s=p.read_text();s=s.replace('input wire [4:0] read_at,output reg [7:0] read_data,output reg fault);','input wire [9:0] read_at,input wire meta_write,input wire [7:0] meta_data,output reg [7:0] read_data,output reg fault);')
 s=s.replace('memory[0:31]','memory[0:1023]');s=once(s,'always @(posedge host_clk)read_data<=memory[read_at];','always @(posedge host_clk)begin read_data<=memory[read_at];if(meta_write&&!rst)memory[read_at]<=meta_data;end');p.write_text(s,newline='\n')
 (d/'nes_stage396.sv').write_text((ROOT/'src/fpga/nes_joint396/nes_stage396.sv').read_text(),newline='\n')
 (d/'nes_check396.sv').write_text((ROOT/'src/fpga/nes_joint396/nes_check396.sv').read_text(),newline='\n')
 p=d/'nes_mux260.sv';s=p.read_text();a=s.index(' wire begin_ready,');z=s.index(' assign tile_closed267=',a)
 s=s[:a]+''' wire begin_ready,put_ready,chunk_ready,pe,ce,aoe,tile_empty396;wire [7:0] aperture_data,tile_q;reg [10:0] scroll_length;
 wire aperture_begin=state==OPEN&&!reference;
 wire aperture_put=(state==PUT&&op!=8'had)||state==EXPAND;
 wire [7:0] aperture_byte=state==EXPAND?seed[(produced[1:0]&(mode==3?2'd3:2'd1))*8+:8]:held;
 wire consume=state==TAKE&&!reference;
 wire word_valid,word_ready,word_end,word_partial,word_kind;wire [15:0] word_generation;wire [9:0] word_slot;wire [5:0] word_length;
 wire [9:0] meta_address396;wire meta_write396;wire [7:0] meta_data396;wire tile_fault;
 nes_tile_link394 tile_link(.nes_clk(nes_clk),.host_clk(host_clk),.reset(rst),.source_fault(failed||qfault||pe||ce),
  .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(tile_generation),
  .end_valid(end_valid),.end_partial(end_partial295),.end_ready(end_ready),.end_generation(end_generation),
  .word_valid(word_valid),.word_ready(word_ready),.word_end(word_end),.word_partial(word_partial),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),
  .read_at(meta_address396),.meta_write(meta_write396),.meta_data(meta_data396),.read_data(tile_q),.fault(tile_fault));
 nes_stage396 aperture(.clk(host_clk),.reset(rst),.active(!fault&&have_identity),.begin_valid(aperture_begin),.begin_tile(mode==0),.begin_length(chunk_length),.begin_token(allocation),
  .generation(identity[47:32]),.kind(region==1),.first(canonical[9:0]),.begin_ready(begin_ready),.byte_valid(aperture_put),.byte_data(aperture_byte),.byte_ready(put_ready),.seal(state==SEAL),
  .producer_error(pe),.chunk_ready(chunk_ready),.consume(consume),.consume_token(chunk_token),.consume_error(ce),.tile_empty(tile_empty396),
  .word_valid(word_valid),.word_end(word_end),.word_kind(word_kind),.word_generation(word_generation),.word_slot(word_slot),.word_length(word_length),.word_ready(word_ready),
  .meta_address(meta_address396),.meta_write(meta_write396),.meta_data(meta_data396),.meta_q(tile_q),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(aperture_data),.oe_n(aoe));
 wire accept_end=word_valid&&word_end&&word_ready;
'''+s[z:]
 s=s.replace('reg [4:0] tile_at;reg [11:0] tile_bytes;','')
 s=s.replace('tile_at<=0;tile_bytes<=0;','').replace('seed<=0;tile_bytes<=0;','seed<=0;')
 s=s.replace('&&!active_fragment&&!rst&&!fault;','&&!active_fragment&&tile_empty396&&!rst&&!fault;')
 # Binding is in the shared store,not a second host tile-copy FSM.
 a=s.index('    TILECHECK:');z=s.index('    SEAL:',a);s=s[:a]+s[z:]
 s=s.replace('else if(mode==0)state<=TILECHECK;else state<=GET;','else if(mode==0)begin if(records_left==1)qretire<=1;state<=EXPOSE;end else if(mode>1&&fragment_at!=0)state<=EXPAND;else state<=GET;')
 s=s.replace('||decoded==0||decoded[3:0]!=0','||decoded==0||decoded>2048||decoded[3:0]!=0').replace('||decoded==0||decoded[4:0]!=0','||decoded==0||decoded>2048||decoded[4:0]!=0')
 s=s.replace('last_fragment<=1;produced<=0;seed<=0;','last_fragment<=!(mode>1&&!zero_tail&&decoded>512);produced<=0;seed<=0;')
 s=s.replace('zero_tail?12\'d2:decoded[11:0]','zero_tail?12\'d2:mode>1&&decoded>512?12\'d512:decoded[11:0]')
 s=s.replace("if(op==8'h92||records_left==1)qretire<=1;", "if((op==8'h92||records_left==1)&&!(mode>1&&fragment_at!=0))qretire<=1;")
 s=s.replace("     if(op==8'h92)begin\n      consume_record312", "     if(op!=8'h92&&mode>1&&!last_fragment)begin\n      fragment_at<=fragment_at+chunk_length;chunk_length<=source_total-fragment_at-chunk_length>512?512:source_total-fragment_at-chunk_length;\n      first_fragment<=0;last_fragment<=source_total-fragment_at-chunk_length<=512;produced<=0;state<=OPEN;\n     end else if(op==8'h92)begin\n      consume_record312")
 a=s.index(' wire [16:0] last_byte=');z=s.index(' // Physical response capture',a)
 s=s[:a]+''' wire bad_record,checked396;
 nes_check396 record_check(.clk(host_clk),.reset(rst),.start(state==RCHECK),.bank(identity[48]),.record(record394),.done(checked396),.bad(bad_record));
'''+s[z:]
 s=s.replace('DVIEW,DONE} state_t','DVIEW,DONE,RVALIDATE} state_t')
 s=once(s,'    RCHECK:begin','    RCHECK:state<=RVALIDATE;\n    RVALIDATE:if(checked396)begin')
 p.write_text(s,newline='\n')
 # A fixed immutable view shares one byte lane between CRC8 and response.
 # Constant padding stays constant,instead of rotating through200 flipflops.
 p=d/'nes_spi270.sv';s=p.read_text()
 s=once(s,'reg [199:0] snapshot;', 'reg [175:0] view396;reg [7:0] first396;')
 s=s.replace('snapshot[199:192]','lane396').replace("snapshot<=0;","view396<=0;first396<=0;")
 s=s.replace('    snapshot<={snapshot[191:0],snapshot[199:192]};\n','')
 # The previous replacement touched the rotation RHS;remove both spellings.
 s=s.replace('    snapshot<={snapshot[191:0],lane396};\n','').replace('      snapshot<={snapshot[191:0],lane396};\n','')
 s=s.replace('reply_byte315<=snapshot[191:184];','reply_byte315<=lane396;')
 s=s.replace("snapshot<={source_status[183:0],16'd0};", "first396<=source_status[183:176];view396<=source_status[175:0];")
 s=s.replace("snapshot<={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],output_status[127:96],output_status[63:8],16'd0};", "first396<=8'hfb;view396<={output_status[175:128],plan_status[167:144],output_status[199:184],output_status[127:96],output_status[63:8]};")
 s=s.replace("snapshot<={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],104'd0};", "first396<=8'hfb;view396<={output_status[175:128],plan_status[167:144],output_status[199:184],88'd0};")
 s=s.replace('wire [7:0] crc_byte=', '''wire [4:0] lane_address396=byte_event?count[4:0]:crc_at;
 wire [7:0] lane396=lane_address396==0?first396:lane_address396<=22?view396[175-(lane_address396-1)*8-:8]:8'd0;
 wire [7:0] crc_byte=''')
 assert not any(x in s for x in('snapshot<=','snapshot['))
 p.write_text(s,newline='\n')
 from nes_control396 import apply
 apply(d)
