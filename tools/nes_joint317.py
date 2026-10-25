# SPDX-License-Identifier: MIT
"""Validator-owned canonical replay cursor and terminal check sequence."""
from nes_delta231 import once

def apply(d):
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,V_FINAL317} state_t;')
    s=once(s,"assign manifest_at282=map_phase305?cursor[8:0]:9'd0;",
        "assign manifest_at282=rec_i<24?{1'b0,rec_i}:map_phase305?cursor[8:0]+9'd190:cursor[8:0]+9'd24;")
    s=once(s,'if(v_raw)state<=H_HASHREAD;else digest_ready<=1;',
        "if(v_raw)state<=H_HASHREAD;else begin digest_ready<=1;checksum<=16'hffff;state<=H_CERTREAD;end")
    s=once(s,'if(h_count==31)begin digest<=crc_result;digest_ready<=1;state<=V_ACTIVE;end',
        "if(h_count==31)begin digest<=crc_result;digest_ready<=1;checksum<=16'hffff;h_count<=0;state<=H_CERTREAD;end")
    s=once(s,'if(h_count==31)begin certificate_ok<=1;state<=V_ACTIVE;end',
        'if(h_count==31)begin certificate_ok<=1;state<=V_FINAL317;end')
    s=once(s,'    default:fault<=6;', '''    V_FINAL317:begin
     if(!map_phase305||cursor!=256||rec_i!=24||!v_all_consumed||!certificate_ok||!digest_ready)fault<=3;
     else begin h_count<=0;seal_state<=1;state<=V_WAITDISPLAY;end
    end
    default:fault<=6;''')
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'canonical_read313?manifest_byte313:', 'canonical_read313?manifest_at282:')
    s=once(s,'held<=qdata;display_byte313<=manifest_byte313<24;', 'held<=qdata;display_byte313<=manifest_at282<24;')
    s=once(s,"if(manifest_byte313==445)state<=MHASH313;\n       else begin manifest_byte313<=manifest_byte313+1'b1;state<=MREAD313;end",
        'if(manifest_at282==446)state<=MHASH313;\n       else state<=MREAD313;')
    s=once(s,'assign ordinary_finish=state==MFINISH313&&range_ready&&!rst&&!fault;', 'assign ordinary_finish=0;')
    s=s.replace('tap_start278||state==MHASH313||state==MCERT313','tap_start278||state==MHASH313')
    s=s.replace("state==MCERT313?2'd2:",'')
    a=s.index('     MHASH313:if(range_ready)');b=s.index('     MSEALWAIT313:',a)
    s=s[:a]+'     MHASH313:if(range_ready)state<=MSEALWAIT313;\n'+s[b:]
    # Remove unreachable completion states from the shared metadata decoder.
    for name in ('MHASHWAIT313','MCERT313','MCERTWAIT313','MFINISH313'):
        s=s.replace('||state=='+name,'')
    p.write_text(s,newline='\n')
