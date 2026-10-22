# SPDX-License-Identifier: MIT
"""Phase-owned host packet position and validator RAM cursor; checks retained."""
import re
from nes_delta231 import once

def apply(d):
 p=d/'nes_mux260.sv';s=p.read_text()
 s=once(s,'reg [7:0] at,held,parser_address;', 'reg [7:0] at,held;reg [8:0] parser_address;')
 s=once(s,':parser_address;', ':parser_address[7:0];')
 s=once(s,'reg [8:0] opos,oend;', 'wire [8:0] opos=parser_address,oend=qlen;')
 s=re.sub(r'\bopos<=([^;]+);','',s);s=re.sub(r'\boend<=([^;]+);','',s)
 assert 'opos<=' not in s and 'oend<=' not in s
 p.write_text(s,newline='\n')
 p=d/'nes_validator278.sv';s=p.read_text()
 s=once(s,'reg [9:0] cursor,v_addr;', 'reg [11:0] cursor;reg [9:0] v_addr;')
 s=once(s,'reg [11:0] v_bit_at,v_end283,v_map_end;', 'wire [11:0] v_bit_at=cursor;reg [11:0] v_end283,v_map_end;')
 s=once(s,'assign manifest_at282=cursor>=166?', 'wire receipt_walk296=state==V_RREAD||state==V_RWRITE||state==V_PREAD||state==V_PWRITE;\n assign manifest_at282=!receipt_walk296&&cursor>=166?')
 s=once(s,'assign manifest_started282=rec_i!=0||cursor!=0;', 'assign manifest_started282=rec_i!=0||(!receipt_walk296&&cursor!=0);')
 s=once(s,'if(next_byte283>=v_end283)state<=V_ACTIVE;else begin v_bit_at<=next_byte283;', 'if(next_byte283>=v_end283)begin cursor<=0;state<=V_ACTIVE;end else begin cursor<=next_byte283;')
 s=once(s,'v_bit_at<=0;', '')
 s=once(s,'v_bit_at<=v_first;', 'cursor<=v_first;')
 assert 'v_bit_at<=' not in s
 p.write_text(s,newline='\n')
