# SPDX-License-Identifier: MIT
"""Share phase-exclusive receipt/expected cursor and active ingress record."""
from nes_joint327 import apply as previous
from nes_delta231 import once

def apply(d):
    previous(d)
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,' reg [8:0] manifest_byte313;','')
    pos=s.index(' wire requirements313=')
    s=s[:pos]+" wire [8:0] manifest_byte313=active305.start[8:0];\n"+s[pos:]
    s=s.replace('manifest_byte313<=','active305.start<=')
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'reg [9:0] cursor,v_addr;', 'reg [11:0] cursor;reg [9:0] v_addr;')
    s=once(s,'reg [11:0] v_bit_at,v_end283,v_map_end;', 'reg [11:0] v_end283,v_map_end;')
    s=once(s,'v_initialized<=0;v_bit_at<=0;', 'v_initialized<=0;')
    s=s.replace('v_bit_at','cursor')
    s=once(s,'if(next_byte283>=v_end283)begin state<=V_ACTIVE;', 'if(next_byte283>=v_end283)begin cursor<=0;state<=V_ACTIVE;')
    p.write_text(s,newline='\n')
