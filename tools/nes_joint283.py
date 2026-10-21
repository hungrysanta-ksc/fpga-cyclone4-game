# SPDX-License-Identifier: MIT
"""One admitted receipt range and one RAM byte cursor; compact wire unchanged."""
from nes_delta231 import once
from nes_joint282 import patch as previous, apply as previous_apply


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    # The validator owns the complete range until its RAM walk finishes.
    # Host payload/DMA/ordered-ACK predicates still precede these requests.
    s=once(s,"receipt_first282=opos;receipt_count282=oend-opos>16?12'd16:oend-opos;",
        'receipt_first282=opos;receipt_count282=oend-opos;')
    s=once(s,'receipt_end282=opos+receipt_count282;receipt_valid282=1;',
        'receipt_end282=oend;receipt_valid282=1;')
    s=once(s,"receipt_first282=1152+(opos>>4);receipt_end282=oend-opos>256?opos+12'd256:oend;",
        'receipt_first282=1152+(opos>>4);receipt_end282=oend;')
    s=once(s,"    if(receipt_end282-opos>256)receipt_end282=opos+12'd256;\n",'')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'reg [11:0] v_bit_at,v_left,v_map_end;reg [3:0] v_take;',
        'reg [11:0] v_bit_at,v_end283,v_map_end;')
    a=s.index(' wire [3:0] v_available=');b=s.index(' assign v_ready=',a)
    s=s[:a]+''' // Admission computes the exclusive end once. The RAM walk advances
 // at byte boundaries, without a second remaining-count/subrange machine.
 wire [12:0] range_end283={1'b0,v_first}+{1'b0,v_count};
 wire [12:0] domain_end283=v_map_range?13'd2048:
  v_first<1024?13'd1024:v_first<1152?13'd1152:
  v_first<1184?13'd1184:v_first<1312?13'd1312:13'd1328;
 wire [11:0] next_byte283={v_bit_at[11:3]+9'd1,3'b000};
 wire [7:0] first_mask283=8'hff<<v_bit_at[2:0];
 wire [7:0] last_mask283=v_bit_at[11:3]==v_end283[11:3]?
  ~(8'hff<<v_end283[2:0]):8'hff;
 wire [7:0] v_nextmask=first_mask283&last_mask283;
'''+s[b:]
    s=once(s,'begin if(v_left==v_take)state<=V_ACTIVE;else begin v_bit_at<=v_bit_at+v_take;v_left<=v_left-v_take;state<=V_RREAD;end end',
        'begin if(next_byte283>=v_end283)state<=V_ACTIVE;else begin v_bit_at<=next_byte283;state<=V_RREAD;end end')
    s=s.replace('v_left<=0;','v_end283<=0;').replace('v_take<=0;','')
    old="if(rec_i!=0||cursor!=0||!v_count||v_count>(v_map_range?32:16)||(!v_map_range&&v_first<1024&&v_first+v_count>1024)||(!v_map_range&&v_first<1152&&v_first+v_count>1152)||{1'b0,v_first}+{1'b0,v_count}>(v_map_range?13'd2048:13'd1328)||(v_map_range&&(v_first<v_map_end||v_count>32)))fault<=2;"
    s=once(s,old,"if(rec_i!=0||cursor!=0||!v_count||range_end283>domain_end283||(v_map_range&&(v_first<v_map_end||v_count>32))||(!v_map_range&&v_first>=1312&&v_count!=1))fault<=2;")
    s=once(s,'v_bit_at<=v_first;v_left<=v_count;v_mapmode<=v_map_range;if(v_map_range)v_map_end<=v_first+v_count;',
        'v_bit_at<=v_first;v_end283<=range_end283[11:0];v_mapmode<=v_map_range;if(v_map_range)v_map_end<=range_end283[11:0];')
    s=once(s,'v_mask<=v_nextmask;v_take<=v_ntake;', 'v_mask<=v_nextmask;')
    assert 'v_left' not in s and 'v_take' not in s
    p.write_text(s,encoding='utf-8',newline='\n')


def from280(d):
    previous_apply(d);apply(d)


def patch(d):
    previous(d);apply(d)
