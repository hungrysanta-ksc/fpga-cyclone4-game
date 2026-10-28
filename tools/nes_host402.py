# SPDX-License-Identifier: MIT
"""Fixed semantic host prototype; no byte VM/program/IO interpreter remains.
The fixed396 semantics are the reference.400 read-end ownership and current
SPI/queue/hint/plan ABI are retained, rather than resurrecting old ingress.
REJECTED: header402 exposes missing staged-header publication gating; the
whole control also grows. Preserve the measured prototype, do not promote it.
"""
from nes_delta231 import BASE,ROOT,once

def apply(d):
 current=(d/'nes_mux260.sv').read_text();old=(BASE/'probes/nes-joint396/build08/nes_mux260.sv').read_text()
 s=current[:current.index(' wire rst=')]+old[old.index(' wire rst='):]
 s=s.replace('nes_queue260 queue(',"nes_queue260 queue(.irq398(),.control_write398(1'b0),.control_address398(8'd0),.control_q398(),")
 s=s.replace('nes_tile_link394 tile_link(', 'nes_tile_link394 tile_link(.hint_metaactive398(hint_metaactive398),.hint_meta_at398(hint_meta_at398),.hint_meta_q398(hint_meta_q398),')
 s=s.replace('nes_stage396 aperture(', 'nes_stage396 aperture(.meta_pause398(tag_grant402),.meta_atomic398(stage_atomic402),')
 s=s.replace('wire [9:0] meta_address396;wire meta_write396;wire [7:0] meta_data396;', 'wire [9:0] stage_address402;wire stage_write402;wire[7:0]stage_data402;wire stage_atomic402;\n wire tag_grant402=tag_write400&&!stage_atomic402&&!rst&&!fault;assign tag_ready400=tag_grant402;\n wire[9:0]meta_address396=tag_grant402?10\'d928+tag_at400:stage_address402;wire meta_write396=tag_grant402||stage_write402;wire[7:0]meta_data396=tag_grant402?tag_data400:stage_data402;')
 # Only the stage instance changes to the private stage side of the arbiter.
 s=once(s,'.meta_address(meta_address396),.meta_write(meta_write396),.meta_data(meta_data396),.meta_q(tile_q)', '.meta_address(stage_address402),.meta_write(stage_write402),.meta_data(stage_data402),.meta_q(tile_q)')
 s=s.replace('reg [11:0] chunk_length,read_count,produced;reg [15:0] tap_position;', 'reg[11:0]chunk_length,produced;wire[11:0]read_count;wire[15:0]tap_position;reg[15:0]tap_base402;')
 s=s.replace('reg tap_seen,read_pending,tap_fault;', 'wire tap_seen,read_pending,tap_fault;wire[7:0]read_data402;wire read_event402;')
 s=s.replace(' wire read_end=rs&&!rp;',' assign read_end=rs&&!rp;')
 a=s.index(' assign read359=');b=s.index(' wire write_end=',a)
 s=s[:a]+''' wire read_end;
 assign read359={read_event402,crc_byte,crc_start,read_op,region[2:0],tap_position,read_data402};
 nes_read_owner400 read_owner(.clk(host_clk),.reset(rst),.stop(fault),.active(state==WAITREAD),
  .start(state==OPEN&&(reference||begin_ready)&&!footer_active396),.clear(state==TAKE),.read_n(read_n),.capture(capture),
  .ended(read_end&&ap>=24'h400800&&ap<24'h401800&&!invalidate_banks),.checker_ready(ready359),
  .address(address),.ended_address(ap),.data(aperture_data),.token(chunk_token),.length(chunk_length),
  .base_position(tap_base402),.map_stride(region==2&&stride32),.count(read_count),.position(tap_position),
  .held_data(read_data402),.seen(tap_seen),.pending(read_pending),.fault(tap_fault),.event_valid(read_event402));
'''+s[b:]
 s=s.replace('read_count<=0;','').replace('tap_seen<=0;read_pending<=0;tap_fault<=0;','')
 a=s.index('   if(read_n)tap_seen');b=s.index('   if(accept_end)',a);s=s[:a]+s[b:]
 s=s.replace('tap_position<=','tap_base402<=')
 s=s.replace('read_count==chunk_length&&ready359&&mask','read_count==chunk_length&&ready359&&!read_pending&&mask')
 s=s.replace('.source_fault(failed||qfault||pe||ce)', '.source_fault(fault)')
 s=s.replace('footer_phase396&&!rst;', 'footer_phase396&&!rst&&!fault;')
 # Reference396 left a separate fragment position conversion for tiles;
 # use the same canonical byte base as400's bounds-checked ABI.
 s=s.replace('region==2?(canonical<<1)+(stride32?(offset<<5):offset):canonical+offset', 'region==2?(canonical<<1)+(stride32?(offset<<5):offset):(canonical<<(region==1?5:region==0?4:0))+offset')
 # No generic context port exists. Header is the single active record,
 # not a second VM context RAM copy. Metadata arbitration now has only tag
 # versus stage, and the current immutable token/position remain hot.
 at=s.rindex('endmodule')
 debug='''
 wire[2:0]phase=state==WAITREAD?3'd1:state==ENDWAIT?3'd2:state==DVIEW?3'd3:state==DONE?3'd5:sealed&&view_at==12?3'd4:3'd0;
 wire finish_pending=state==ENDWAIT;
 // synthesis translate_off
`ifndef SYNTHESIS
 wire handler=0;wire[11:0]debug_pc=state;
`endif
 // synthesis translate_on
'''
 s=s[:at]+debug+s[at:]
 assert 'nes_byte398'not in s and 'program398'not in s and 'IO_'not in s
 (d/'nes_mux260.sv').write_text(s,newline='\n')
 (d/'nes_check396.sv').write_text((ROOT/'src/fpga/nes_joint396/nes_check396.sv').read_text(),newline='\n')
