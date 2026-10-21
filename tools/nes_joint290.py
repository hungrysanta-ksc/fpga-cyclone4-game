# SPDX-License-Identifier: MIT
"""Uniform exclusive receipt endpoints for ordinary and map RAM walks."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'receipt_count282=receipt_limit287-receipt_first282;\n   receipt_valid282=receipt_count282!=0;',
        'receipt_count282=receipt_limit287; // descriptor port carries exclusive end\n   receipt_valid282=receipt_limit287>receipt_first282;')
    s=once(s,'assign range_count=count;', 'assign range_count=first+count; // exclusive map endpoint\n')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,"wire [12:0] range_end283={1'b0,v_first}+{1'b0,v_count};", "wire [12:0] range_end283={1'b0,v_count}; // uniform exclusive endpoint")
    s=once(s,'cursor!=0||!v_count||range_end283>domain_end283','cursor!=0||range_end283<={1\'b0,v_first}||range_end283>domain_end283')
    s=once(s,'v_count>32', "range_end283>{1'b0,v_first}+13'd32")
    s=once(s,'v_count!=1', "range_end283!={1'b0,v_first}+13'd1")
    p.write_text(s,encoding='utf-8',newline='\n')
