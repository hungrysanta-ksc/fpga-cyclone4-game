# SPDX-License-Identifier: MIT
"""One admitted immutable identity for host execution and independent checks.

The mailbox is copied only by its host owner. Validator checks still compare
incoming H2/BEGIN against that original identity; H2 cannot replace it. STOP
freezes use, final ACK releases it, and serial/token history remains separate.
"""
from nes_delta231 import once


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'reg [48:0] identity;','reg [83:0] admitted286;wire [48:0] identity=admitted286[48:0];')
    s=once(s,'assign grant_epoch278=full_idata278[83:52];assign grant_raw278=full_idata278[51:49];',
           'assign grant_epoch278=admitted286[83:52];assign grant_raw278=admitted286[51:49];')
    s=once(s,'assign grant_generation278=idata[47:32];assign grant_serial278=idata[31:0];',
           'assign grant_generation278=identity[47:32];assign grant_serial278=identity[31:0];')
    s=once(s,';identity<=0;',';admitted286<=0;')
    s=once(s,'identity<=idata;','admitted286<=full_idata278;')
    s=once(s,'reg [2:0] prelude_raw;','wire [2:0] prelude_raw=admitted286[51:49];')
    s=once(s,'prelude_raw<=0;','')
    s=once(s,'      if(prelude_mode&&at==20)prelude_raw<=held[2:0];\n','')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'reg [2:0] admitted_raw,v_raw;', 'wire [2:0] admitted_raw=grant_raw278,v_raw=grant_raw278;')
    s=once(s,'reg active,initialized,seal_state,v_bank,v_mapmode,external_range;',
           'reg active,initialized,seal_state,v_mapmode,external_range;wire v_bank=~grant_serial278[0];')
    s=once(s,'reg [31:0] epoch,base_serial;reg [15:0] generation,checksum,digest;',
           'wire [31:0] epoch=grant_epoch278,base_serial=grant_serial278;wire [15:0] generation=grant_generation278;reg [15:0] checksum,digest;')
    s=once(s,'epoch<=0;base_serial<=0;generation<=0;admitted_raw<=0;v_raw<=0;v_bank<=0;', '')
    s=once(s,'     epoch<=grant_epoch278;base_serial<=grant_serial278;generation<=grant_generation278;\n     admitted_raw<=grant_raw278;', '     ')
    s=s.replace('v_raw<=v_raw_count;','').replace('v_bank<=v_target_bank;','')
    assert 'v_raw<=' not in s and 'v_bank<=' not in s
    p.write_text(s,encoding='utf-8',newline='\n')
