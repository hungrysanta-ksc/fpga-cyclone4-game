# SPDX-License-Identifier: MIT
"""Publish the final map batch before ordinary planning; one final RAM job."""
from nes_delta231 import once
from nes_completion331 import native as previous_native


def native(d):
    previous_native(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned map(unsigned at,',
           '''unsigned publish_map332(void){
 /* When work is already queued, prepare ordinary data while it drains.
  * Only an observed empty storage queue needs the early map wake-up.
  * Cached progress is conservative: no extra E0/E2 just for this decision. */
 if((uint16_t)(state259.sent-state259.retired))return !state259.error;
 return flush260();
}
static unsigned map(unsigned at,''')
    p.write_text(s,newline='\n')
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'extern unsigned dispatch289(const uint8_t *,unsigned);',
           'extern unsigned dispatch289(const uint8_t *,unsigned);\nextern unsigned publish_map332(void);')
    s=once(s,'if(!map247(s,p,r->target)||!dirty_span231',
           'if(!map247(s,p,r->target)||!publish_map332()||!dirty_span231')
    p.write_text(s,newline='\n')


def apply(d):
    # Queue port B stays exclusively leased to the SEAL head until v_sealed.
    # The validator owns an independent expected cursor and phase-RAM reads.
    ports='input wire [7:0] expected_data332,output wire [8:0] expected_addr332,'
    connect='.expected_data332(expected_data332),.expected_addr332(expected_addr332),'
    for name,module in [('nes_validator278.sv','nes_validator278'),('nes_joint257.sv','nes_joint257')]:
        p=d/name;s=p.read_text();s=once(s,'module '+module+'(', 'module '+module+'('+ports)
        if name=='nes_joint257.sv':s=once(s,'nes_validator278 validator(', 'nes_validator278 validator('+connect)
        p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' wire display_write,',' wire [7:0] expected_data332;wire [8:0] expected_addr332;\n wire display_write,')
    s=once(s,' flow(', ' flow('+connect);s=once(s,'nes_joint257 core(', 'nes_joint257 core('+connect)
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'output wire queue_admit319,','output wire [7:0] expected_data332,input wire [8:0] expected_addr332,output wire queue_admit319,')
    s=once(s,'''canonical_read313?manifest_byte313:
  display_byte313?parser_address-9'd17:
  header[0]==15?manifest_byte313+9'd24:manifest_byte313+9'd190;''', '''canonical_read313?expected_addr332:
  display_byte313?{4'b1110,(parser_address[4:0]-5'd17)}:
  {header[0]==15,manifest_byte313[7:0]};''')
    s=once(s,'canonical_address313>=446','canonical_bad332')
    s=once(s,' wire canonical_write313=header[0]!=3&&state==MISSUE313&&!rst&&!fault;', ''' wire canonical_bad332=!display_byte313&&
  (header[0]==15?manifest_byte313>=9'd166:manifest_byte313[8]);
 wire canonical_write313=header[0]!=3&&state==MISSUE313&&!rst&&!fault&&!canonical_bad332;''')
    s=once(s,' wire canonical_read313=', ' assign expected_data332=qdata;\n wire canonical_read313=')
    s=once(s,'assign display_write=canonical_read313&&state==MISSUE313&&display_byte313&&range_ready&&!rst&&!fault;', "assign display_write=1'b0;")
    s=once(s,'assign ordinary_check=canonical_read313&&state==MISSUE313&&!display_byte313&&range_ready&&!rst&&!fault;', "assign ordinary_check=1'b0;")
    s=once(s,'assign ordinary_finish=state==MFINISH313&&range_ready&&!rst&&!fault;', 'assign ordinary_finish=header[0]==3&&state==MREAD313&&range_ready&&!rst&&!fault;')
    s=once(s,'assign ordinary_hash_start=(tap_start278||state==MHASH313||state==MCERT313)&&range_ready&&!rst&&!fault;', 'assign ordinary_hash_start=tap_start278&&range_ready&&!rst&&!fault;')
    s=once(s,"assign ordinary_hash_kind=state==MHASH313?2'd3:state==MCERT313?2'd2:tap_raw278?2'd0:2'd1;", "assign ordinary_hash_kind=tap_raw278?2'd0:2'd1;")
    s=once(s,'MREAD313:state<=MCAP313;', 'MREAD313:if(header[0]!=3)state<=MCAP313;else if(range_ready)state<=MSEALWAIT313;')
    s=once(s,'      if(header[0]==3)begin\n       held<=qdata;display_byte313<=manifest_byte313<24;state<=MISSUE313;\n      end else if', '      if')
    s=once(s,"      if(header[0]==3)begin\n       if(manifest_byte313==445)state<=MHASH313;\n       else begin manifest_byte313<=manifest_byte313+1'b1;state<=MREAD313;end\n      end else begin", '      begin')
    a=s.index('     MHASH313:if(range_ready)');b=s.index('     MSEALWAIT313:',a)
    s=s[:a]+s[b:]
    s=once(s,'MWAIT313=46,MDONE313=47,MHASH313=48,MHASHWAIT313=49,\n  MCERT313=50,MCERTWAIT313=51,MFINISH313=52,MSEALWAIT313=53;', 'MWAIT313=46,MDONE313=47,MSEALWAIT313=53;')
    s=once(s,'||state==MHASH313||state==MHASHWAIT313||state==MCERT313||state==MCERTWAIT313||state==MFINISH313', '')
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,E_READ332,E_CAPTURE332} state_t;')
    s=once(s," wire range_external=1'b1;", " wire range_external=1'b1;\n assign expected_addr332=rec_i<24?{4'b1110,rec_i[4:0]}:{!map_phase305,cursor[7:0]};")
    # No separate scan flag, host byte counter, host hash/certificate handshake,
    # or secondary completion pulse. The RAM job ends only in V_WAITDISPLAY.
    a=s.index(' task advance_check;');b=s.index('\n\n',a)
    s=s[:a]+''' task advance_check;
  begin
   if(!map_phase305&&cursor==165)begin cursor<=0;map_phase305<=1;state<=E_READ332;end
   else if(map_phase305&&cursor==255)begin
    cursor<=256;h_count<=0;
    if(rec_i!=24||!scroll_seen||digest_ready)fault<=7;
    else if(v_raw)begin checksum<=digest;state<=H_HASHREAD;end
    else begin digest_ready<=1;checksum<=16'hffff;state<=H_CERTREAD;end
   end else begin cursor<=cursor+1'b1;state<=E_READ332;end
  end
 endtask'''+s[b:]
    s=once(s,'''     else if(display_write)begin
      if(rec_i>=24||(map_phase305||cursor!=0))fault<=7;else begin v_value<=v_check_value;state<=D_READ;end
     end else if(h_start)begin''', '''     else if(h_start)begin''')
    a=s.index('      end else if(h_kind==3');b=s.index('      end else fault<=7;',a)
    s=s[:a]+s[b:]
    a=s.index('     end else if(v_check_valid)begin');b=s.index('\n     end\n    end',a)
    s=s[:a]+'''     end else if(v_finish_valid)begin
      if(rec_i!=0||cursor!=0||map_phase305||!v_all_consumed||certificate_ok)fault<=3;
      else state<=E_READ332;'''+s[b:]
    s=once(s,'    V_RREAD:begin', '''    E_READ332:state<=E_CAPTURE332;
    E_CAPTURE332:begin v_value<=expected_data332;state<=rec_i<24?D_READ:V_CHECKREAD;end
    V_RREAD:begin''')
    s=once(s,'build_i<=v_value;rec_i<=rec_i+1\'b1;state<=V_ACTIVE;', 'build_i<=v_value;rec_i<=rec_i+1\'b1;state<=E_READ332;')
    s=once(s,'if(h_count==31)begin digest<=crc_result;digest_ready<=1;state<=V_ACTIVE;end', "if(h_count==31)begin digest<=crc_result;digest_ready<=1;h_count<=0;checksum<=16'hffff;state<=H_CERTREAD;end")
    s=once(s,'if(h_count==31)begin certificate_ok<=1;state<=V_ACTIVE;end', 'if(h_count==31)begin\n       if(!v_all_consumed||!digest_ready||rec_i!=24||!map_phase305||cursor!=256)fault<=3;\n       else begin certificate_ok<=1;h_count<=0;seal_state<=1;state<=V_WAITDISPLAY;end\n      end')
    p.write_text(s,newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text()
    # Map[0:255], requirements[256:421], display[448:471]. Both immutable
    # packet slots still begin at480/752. No new RAM/port or expected copy.
    s=once(s,'expected_address313<446','expected_address313<472')
    p.write_text(s,newline='\n')
