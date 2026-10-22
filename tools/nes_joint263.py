# SPDX-License-Identifier: MIT
"""Consumer event bridge reuses the24-bit receipt mailbox; batch CPU hints.

The executable C consumer is a host model. This bridge is synthesizable RTL;
its costs must not be confused with a completed65816 ordinary executor.
"""
from nes_joint262 import sources as prior
from nes_delta231 import once

PORTS='''output wire ordinary_range,output wire [11:0] ordinary_first,ordinary_count,
 output wire ordinary_stream,output wire [7:0] ordinary_byte,input wire ordinary_stream_ready,
 output wire ordinary_check,ordinary_finish,ordinary_hash_start,ordinary_hash_byte,
 output wire [1:0] ordinary_hash_kind,output wire [3:0] ordinary_hash_index,input wire ordinary_hash_ready,
'''

def sources():
 src=prior();s=src['nes_mux260.sv']
 s=once(s,' output wire context_valid,',PORTS+' output wire context_valid,')
 s=once(s,' wire mv,mready;wire [23:0] md;reg [1:0] ns;', '''wire mv,mready;wire [23:0] md;reg [1:0] ns;
 reg [23:0] consumer_word;reg [2:0] consumer_mask;reg consumer_pending;
 wire consumer_idle=!consumer_pending&&mready;
 wire consumer_event=mv&&md[23:22]==2'b10&&md[21:18]!=0;
 wire [3:0] consumer_kind=md[21:18];
 wire consumer_ready=consumer_kind==2?ordinary_stream_ready:consumer_kind==5?ordinary_hash_ready:range_ready;
 assign ordinary_range=consumer_event&&consumer_kind==1&&consumer_ready&&!rst;
 assign ordinary_first=md[11:0];assign ordinary_count={6'd0,md[17:12]};
 assign ordinary_byte=md[7:0];assign ordinary_stream=consumer_event&&consumer_kind==2&&!rst;
 assign ordinary_check=consumer_event&&consumer_kind==3&&consumer_ready&&!rst;
 assign ordinary_hash_start=consumer_event&&consumer_kind==4&&consumer_ready&&!rst;
 assign ordinary_hash_kind=md[1:0];assign ordinary_hash_index=md[5:2];
 assign ordinary_hash_byte=consumer_event&&consumer_kind==5&&!rst;
 assign ordinary_finish=consumer_event&&consumer_kind==6&&consumer_ready&&!rst;
 ''')
 s=once(s,'.src_valid(state==SEND||(prelude_mode&&state==PUT)||state==BSTART)', '.src_valid(consumer_pending||state==SEND||(prelude_mode&&state==PUT)||state==BSTART)')
 s=once(s,'.src_data(state==SEND?', '.src_data(consumer_pending?consumer_word:state==SEND?')
 s=once(s,'.dst_ready(md[23]?(md[22]?range_ready:context_ready):ns==3)', '.dst_ready(consumer_event?consumer_ready:md[23]?(md[22]?range_ready:context_ready):ns==3)')
 s=once(s,'context_valid=mv&&md[23]&&!md[22]&&!rst', "context_valid=mv&&md[23:18]==6'b100000&&!rst")
 s=once(s,'   written<=0;mask<=0;', '   consumer_word<=0;consumer_mask<=0;consumer_pending<=0;\n   written<=0;mask<=0;')
 s=once(s,'   sealed_sync<=', '   if(consumer_pending&&mready)consumer_pending<=0;\n   sealed_sync<=')
 s=once(s,'    if(write_end)begin', '''    if(write_end)begin
     if(ap>=24'h006060&&ap<=24'h006062)begin
      if(state!=NORMAL||!begun||!consumer_idle)failed<=1;
      else begin consumer_word[ap[1:0]*8+:8]<=dp;consumer_mask[ap[1:0]]<=1;end
     end
     if(ap==24'h006063)begin
      consumer_mask<=0;
      if(state!=NORMAL||!begun||!consumer_idle||consumer_mask!=7||dp!=8'ha5||
         consumer_word[23:22]!=2'b10||consumer_word[21:18]==0||consumer_word[21:18]>6)failed<=1;
      else consumer_pending<=1;
     end
     if(ap==24'h00601c&&!consumer_idle)failed<=1;''')
 s=once(s,"   8'h51:control=receipt_committed;", "   8'h53:control=state==DMA&&batch?remaining:0;\n   8'h64:control=consumer_idle;\n   8'h51:control=receipt_committed;")
 src['nes_mux260.sv']=s
 s=src.pop('nes_joint262.sv').replace('nes_joint262','nes_joint263')
 widths={'v_range_valid':'','v_map_range':'','v_first':'[11:0]','v_count':'[11:0]',
  'v_check_valid':'','v_check_value':'[7:0]','v_finish_valid':'','v_all_consumed':'',
  'stream_valid':'','stream_data':'[7:0]','h_start':'','h_kind':'[1:0]','h_index':'[3:0]','h_valid':'','h_data':'[7:0]'}
 for n,w in widths.items():s=once(s,f'input wire {w} {n},','')
 s=once(s,' wire [15:0] display_generation;', '\n'.join(f' wire {w} {n};' for n,w in widths.items())+'''
 assign v_map_range=0;assign v_all_consumed=1;
 assign stream_data=v_check_value;assign h_data=v_check_value;
 wire [15:0] display_generation;''')
 s=once(s,'.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),', '''.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),
 .ordinary_range(v_range_valid),.ordinary_first(v_first),.ordinary_count(v_count),
 .ordinary_stream(stream_valid),.ordinary_byte(v_check_value),.ordinary_stream_ready(stream_ready),
 .ordinary_check(v_check_valid),.ordinary_finish(v_finish_valid),.ordinary_hash_start(h_start),.ordinary_hash_byte(h_valid),
 .ordinary_hash_kind(h_kind),.ordinary_hash_index(h_index),.ordinary_hash_ready(h_ready),''')
 src['nes_joint263.sv']=s
 return src
