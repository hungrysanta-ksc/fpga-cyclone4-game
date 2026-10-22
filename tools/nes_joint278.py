# SPDX-License-Identifier: MIT
"""Fixed-clock phase RAM: source on NES A, output validator on host B.

Generated from the pinned274/270 boundary. No descriptor/body RPC or shared
cross-clock register aliases. The source mask write uses the next idle slot.
"""
import re
from nes_delta231 import once
from nes_joint276 import queue

GRANT = [
    ("grant278",1),("grant_epoch278",32),("grant_serial278",32),
    ("grant_generation278",16),("grant_raw278",3),("host_ack278",1),
]
RET = [("crc_done278",1),("crc_index278",4),("init278",1)]


def ports(names,direction):
    return "".join(f"{direction} wire "+(f"[{w-1}:0] " if w>1 else "")+n+",\n" for n,w in names)


def binds(names):
    return "".join(f".{n}({n})," for n,_ in names)


def source(s):
    # Keep the source interface for the wrapper but remove all output logic.
    prefix=s[:s.index(' assign ram_a_addr=')]
    prefix=once(prefix,'module nes_core257(', 'module nes_core257(output wire [2:0] source_raw278,')
    regs=s[s.index(' reg base_valid,'):s.index(' assign output_phase=')]
    query=s[s.index(' reg [10:0] q_maps;'):s.index(' // Same 32 certificate')]
    datapath=s[s.index(' wire changed='):s.index(' wire [9:0] v_validbase=')]
    datapath=once(datapath,' wire crc_output=output_phase;', ' wire crc_output=1\'b0;')
    datapath=re.sub(r' wire \[7:0\] crc_byte=.*?;\n',
        ' wire [7:0] crc_byte=transport_crc_pending?transport_byte:byte_data;\n',datapath)
    datapath=datapath.replace(' assign v_sealed=seal_state&&!reset&&!abort_source&&!fault&&lease_ok;','')
    tasks=s[s.index(' task automatic emit_record'):s.index(' always @(posedge clk)begin\n  if(reset)begin')]
    body=s[s.index(' always @(posedge clk)begin\n  if(reset)begin'):s.index('    V_CLEARALL:if(cursor==817)')]
    body=body.replace('state<=V_CLEARALL;', 'state<=IDLE;',1)
    a=body.index('   else if(!fault&&range_dma_done');b=body.index('   else if(!fault)begin',a)
    body=body[:a]+'''   else if(!fault&&v_display_ack&&state!=V_IDLE)fault<=5;
'''+body[b:]
    body+='''    V_IDLE:if(v_display_ack)state<=IDLE;
    default:begin fault<=6;base_valid<=0;end
   endcase
   end
  end
 end
'''
    return prefix+regs+query+'''
 assign output_phase=state==V_IDLE;
 assign source_raw278=admitted_raw;
 reg mask_pending278;reg [8:0] mask_address278;reg [7:0] mask_value278;
 always @(posedge clk)begin
  if(reset||abort_source||fault)begin mask_pending278<=0;mask_address278<=0;mask_value278<=0;end
  else begin
   mask_pending278<=b_we;
   if(b_we)begin mask_address278<=b_addr;mask_value278<=b_w;end
  end
 end
 assign ram_a_addr={1'b1,mask_pending278?mask_address278:a_addr};
 assign ram_a_we=live&&(mask_pending278||a_we);
 assign ram_a_w=mask_pending278?mask_value278:a_w;
 assign ram_b_addr=0;assign ram_b_we=0;assign ram_b_w=0;
 assign v_ready=0;assign v_sealed=0;assign h_ready=0;assign context_ready=0;
 assign display_request_ready=0;assign display_response_valid=0;assign display_response=0;
 assign stream_ready=0;assign sink_valid=0;assign sink_data=0;
 assign sink_kind=0;assign sink_unit=0;assign sink_lane=0;
'''+datapath+tasks+body+'\nendmodule\n'


def validator(s):
    """Retain independently checked semantics, serialize both receipt ports."""
    context=s[s.index(' // Same 32 certificate'):s.index(' wire [4:0] stream_shift=')]
    context=context.replace('ram_b_q','ram_q')
    mask=s[s.index(' wire [9:0] v_validbase='):s.index(' task advance_range;')]
    mask=mask[:mask.index(' always @*begin')]+''' always @*begin
  v_addr=context_addr;v_we=0;v_wdata=0;
  case(state)
   V_CLEARALL,V_CLEARFRAME,V_RAWINVALID:begin v_addr=cursor;v_we=1;end
   V_RREAD,V_RWRITE:begin
    v_addr=(v_mapmode?10'd562:10'd396)+{1'b0,v_bit_at[11:3]};
    v_we=state==V_RWRITE&&(ram_q&v_mask)==0;v_wdata=ram_q|v_mask;
   end
   V_PREAD,V_PWRITE:begin
    v_addr=v_validbase+{1'b0,v_bit_at[11:3]};v_we=state==V_PWRITE;v_wdata=ram_q|v_mask;
   end
   V_CHECKREAD,V_CHECKTEST:v_addr=cursor<144?v_validbase+cursor:cursor<166?10'd396+cursor:10'd562+cursor-10'd166;
   V_PCHECKREAD,V_PCHECKTEST:v_addr=v_validbase+cursor;
   H_WRITELO,H_WRITEHI:begin v_addr=hash_base+{5'd0,hash_index,1'b0}+(state==H_WRITEHI?10'd1:10'd0);
    v_we=1;v_wdata=state==H_WRITELO?checksum[7:0]:checksum[15:8];end
   H_HASHREAD,H_HASHBYTE:v_addr=hash_base+{5'd0,h_count[4:0]};
   D_CHECK:if(rec_i>=12&&rec_i<16&&!display_bad)begin
    v_addr=10'd864+{8'd0,rec_i[1:0]};v_we=1;v_wdata=v_value;end
   V_IDLE:begin v_we=context_write;v_wdata=context_data;end
   default:begin end
  endcase
  if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;
 end
'''
    tasks=s[s.index(' task advance_range;'):s.index(' task automatic emit_record')]
    body=s[s.index('    V_CLEARALL:if(cursor==817)'):s.index('    default:begin fault<=6')]
    body=body.replace('state<=IDLE;end else cursor', 'state<=IDLE;initialized<=1;end else cursor',1)
    # All ranges arrive only after ordered ACK or actual map token consume.
    body=body.replace('state<=V_STREAM;', 'state<=V_RREAD;')
    a=body.index('    V_STREAM:');b=body.index('    V_RREAD:',a);body=body[:a]+body[b:]
    body=body.replace('13\'d1312','13\'d1328')
    body=once(body,'V_RWRITE:if(v_q&v_mask)fault<=2;else advance_range();',
       '''V_RWRITE:if(v_q&v_mask)fault<=2;else if(v_mapmode)advance_range();else state<=V_PREAD;
    V_PREAD:state<=V_PWRITE;
    V_PWRITE:advance_range();''')
    old='''if(v_raw==0&&cursor>=148)advance_check();else if(v_q!=v_value||ram_b_q!=255)fault<=3;else advance_check();'''
    body=once(body,old,'''if(v_raw==0&&cursor>=148)advance_check();
      else begin checked_byte<=v_q;state<=V_PCHECKREAD;end''')
    body=once(body,'    D_READ:state<=D_CHECK;', '''    V_PCHECKREAD:state<=V_PCHECKTEST;
    V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)fault<=3;else advance_check();
    D_READ:state<=D_CHECK;''')
    body=once(body,"H_WRITEHI:begin v_bit_at<=12'd1312+{8'd0,hash_index};v_left<=1;v_mapmode<=0;state<=V_RREAD;end",
        'H_WRITEHI:state<=V_ACTIVE; // Provisional hash, receipt waits for ordered ACK.')
    body=body.replace('v_initialized[v_bank]<=1;seal_state<=0;state<=IDLE;',
                      'v_initialized[v_bank]<=1;seal_state<=0;active<=0;state<=IDLE;')
    body=body.replace('ram_a_q','ram_q').replace('ram_b_q','ram_q')
    func=s[s.index(' function automatic [15:0] crc16'):s.index(' wire crc_output=')]
    states=['IDLE','V_CLEARALL','V_IDLE','V_CLEARFRAME','V_ACTIVE','V_RREAD','V_RWRITE',
            'V_PREAD','V_PWRITE','V_CHECKREAD','V_CHECKTEST','V_PCHECKREAD','V_PCHECKTEST',
            'V_WAITDISPLAY','V_RAWINVALID','H_BYTES','H_WRITELO','H_WRITEHI','H_SCROLL',
            'H_HASHREAD','H_HASHBYTE','H_CERT','H_CERTREAD','H_LENLOREAD','H_LENLO',
            'H_LENHIREAD','H_LENHI','D_READ','D_CHECK','D_FETCH','D_RETURN']
    return '''// SPDX-License-Identifier: MIT
module nes_validator278(
 input wire clk,reset,abort_source,
'''+ports(GRANT,'input')+ports(RET,'output')+'''
 input wire [7:0] ram_q,output wire [9:0] ram_addr,output wire ram_we,output wire [7:0] ram_w,
 input wire display_write,display_request,output wire display_request_ready,
 output wire display_response_valid,input wire display_response_ready,output wire [7:0] display_response,
 input wire v_begin_valid,v_target_bank,input wire [2:0] v_raw_count,
 input wire v_range_valid,v_map_range,input wire [11:0] v_first,v_count,
 input wire v_check_valid,input wire [7:0] v_check_value,
 input wire v_finish_valid,v_all_consumed,output wire v_ready,v_sealed,
 input wire h_start,input wire [1:0] h_kind,input wire [3:0] h_index,
 input wire h_valid,input wire [7:0] h_data,output wire h_ready,
 input wire context_valid,input wire [7:0] context_data,output wire context_ready,
 output reg [3:0] fault
);
 typedef enum logic[5:0] {'''+','.join(states)+'''} state_t;
 state_t state;
 reg active,initialized,seal_state,v_bank,v_mapmode,external_range;
 reg [2:0] admitted_raw,v_raw;reg [1:0] v_initialized;
 reg [9:0] cursor,v_addr;reg v_we;reg [7:0] v_wdata,v_mask,v_value,checked_byte;
 reg [11:0] v_bit_at,v_left,v_map_end;reg [3:0] v_take;
 reg [7:0] rec_i,build_i;reg [15:0] expanded;
 reg [3:0] hash_index,hash_lane;reg [10:0] h_count;
 reg context_complete,display_less,certificate_ok,digest_ready,scroll_seen;
 reg [31:0] epoch,base_serial;reg [15:0] generation,checksum,digest;
 wire lease_ok=active;wire [7:0] v_q=ram_q;
 wire [9:0] hash_base=10'd332+{4'd0,v_bank,5'd0};
 wire context_write;wire [9:0] context_addr;
 wire v_display_ack=host_ack278;
 wire range_external=1'b1;
 assign ram_addr=v_addr;assign ram_we=v_we;assign ram_w=v_wdata;
 assign init278=initialized&&!reset&&!fault;
 assign crc_done278=state==H_WRITEHI&&!reset&&!abort_source&&!fault&&active;
 assign crc_index278=hash_index;
 assign h_ready=!reset&&!abort_source&&!fault&&active&&(state==H_BYTES||state==H_SCROLL);
 assign v_sealed=seal_state&&!reset&&!abort_source&&!fault&&active;
'''+context+func+'''
 wire [7:0] crc_byte=(state==H_HASHBYTE||state==H_CERT)?ram_q:h_data;
 wire [15:0] crc_result=crc16(checksum,crc_byte);
'''+mask+tasks+'''
 always @(posedge clk)begin
  if(reset)begin
   state<=V_CLEARALL;active<=0;initialized<=0;fault<=0;cursor<=0;seal_state<=0;
   epoch<=0;base_serial<=0;generation<=0;admitted_raw<=0;v_raw<=0;v_bank<=0;v_mapmode<=0;
   v_initialized<=0;v_bit_at<=0;v_left<=0;v_map_end<=0;v_take<=0;v_mask<=0;v_value<=0;
   checked_byte<=0;rec_i<=0;build_i<=0;expanded<=0;external_range<=0;
   hash_index<=0;hash_lane<=0;h_count<=0;context_complete<=0;display_less<=0;
   certificate_ok<=0;digest_ready<=0;scroll_seen<=0;checksum<=16'hffff;digest<=0;
  end else if(abort_source)begin if(!fault)fault<=4;active<=0;seal_state<=0;end
  else if(!fault)begin
   if(grant278)begin
    if(state!=IDLE||!initialized||active)fault<=1;
    else begin
     epoch<=grant_epoch278;base_serial<=grant_serial278;generation<=grant_generation278;
     admitted_raw<=grant_raw278;active<=1;context_complete<=0;display_less<=0;rec_i<=0;
     state<=V_IDLE;
    end
   end else if(v_display_ack&&state!=V_WAITDISPLAY)begin fault<=5;seal_state<=0;end
   else case(state)
    IDLE:begin end
'''+body+'''
    default:fault<=6;
   endcase
  end
 end
endmodule
'''


def local_flow(s):
    s=once(s,'(\n input wire [48:0] link270','(\n'+ports(GRANT,'output')+ports(RET,'input')+
        'input wire [31:0] epoch278,input wire [2:0] raw278,\n input wire [48:0] link270')
    s=once(s,'wire [48:0] idata;', 'wire [83:0] full_idata278;wire [48:0] idata=full_idata278[48:0];')
    s=once(s,'#(.WIDTH(49)) admission', '#(.WIDTH(84)) admission')
    s=once(s,'.src_data({bank,generation,serial})','.src_data({epoch278,raw278,bank,generation,serial})')
    s=once(s,'.dst_data(idata)', '.dst_data(full_idata278)')
    s=once(s,'wire can_admit=!have_identity||state==DONE;', '''wire can_admit=init278&&(!have_identity||state==DONE);
 assign grant278=iv&&can_admit&&!rst;
 assign grant_epoch278=full_idata278[83:52];assign grant_raw278=full_idata278[51:49];
 assign grant_generation278=idata[47:32];assign grant_serial278=idata[31:0];
''')
    s=once(s,' assign display_ack=fv&&sealed&&!rst;',
           ' assign host_ack278=final_send&&fr&&!rst;\n assign display_ack=fv&&sealed&&!rst;')
    a=s.index(' nes_native_mailbox206 #(.WIDTH(24)) consumed(')
    b=s.index(' (* altera_attribute=',a)
    s=s[:a]+''' assign mv=state==DREQ||state==OISSUE||state==SEND||(prelude_mode&&state==PUT)||state==BSTART;
 assign md=state==DREQ?{2'b10,4'd8,18'd0}:state==OISSUE?consumer_word:
  state==SEND?{first,count}:state==BSTART?{2'b11,18'd0,prelude_raw,identity[48]}:{2'b10,14'd0,held};
 assign mready=consumer_event?consumer_ready:md[23]?(md[22]?range_ready:context_ready):range_ready;
 assign context_valid=mv&&md[23:18]==6'b100000&&!rst;assign context_data=md[7:0];
 assign begin_valid=state==BSTART&&range_ready&&!rst;
 assign begin_bank=identity[48];assign begin_raw=prelude_raw;
 assign range_first=first;assign range_count=count;assign range_valid=state==SEND&&range_ready&&!rst;
 assign range_dma_done=0;
 wire bv=state==DWAIT?display_response_valid:range_ready;
 wire [7:0] reply=display_response;
 assign display_response_ready=state==DWAIT&&!rst;
'''+s[b:]
    s=once(s,'reg [1:0] sealed_sync;', 'wire [1:0] sealed_sync={2{sealed}};')
    s=s.replace('sealed_sync<=0;','').replace('sealed_sync<={sealed_sync[0],sealed};','')
    s=once(s,'.dst_ready(sealed)', '.dst_ready(1\'b1)')
    s=once(s,'assign display_ack=fv&&sealed&&!rst;', 'assign display_ack=fv&&!rst;')
    s=once(s,'PREWAIT:if(mready)begin', 'PREWAIT:begin')
    s=once(s,'BWAIT:if(mready)begin', 'BWAIT:if(range_ready)begin')
    s=once(s,'OWAIT:if(mready)case', 'OWAIT:case')
    s=once(s,'ORET:begin if(header[0]==3)', 'ORET:if(range_ready||sealed)begin if(header[0]==3)')
    # No ordinary-range completion pulse or separate ns sequencer is needed:
    # the original descriptor is dispatched only after the physical consume ACK.
    s=s.replace('wire [23:0] md;reg [1:0] ns;', 'wire [23:0] md;')
    return s


def tap_flow(s):
    # The existing header admission remains the sole descriptor source.
    a=s.index('       if(manifest_phase!=0||!outlen||',s.index('     OSETUP:begin'))
    b=s.index('       else state<=OSELECT;',a)
    conditions=s[a:b]
    # Move existing data-command checks before exposing the SNES read window.
    conditions=conditions.replace('failed<=1;', 'bad_data278=1;')
    check=''' reg bad_data278;
 always @*begin
  bad_data278=0;
'''+conditions+'''
  if(header[1]==3&&(startpos[3:0]!=0||outlen[3:0]!=0))bad_data278=1;
 end
 wire data_command278=header[0]==2||header[0]==4||header[0]==5||header[0]==8;
'''
    s=s[:a]+'       state<=OSELECT;'+s[b+len('       else state<=OSELECT;'):]
    s=once(s,' wire consumer_event=',check+'''
 // Capture only a tagged, valid SNES bus read, once per physical strobe.
 reg tap_seen278,tap_fault278,tap_repeat278;
 reg [2:0] tap_state278;reg [12:0] tap_pos278;
 reg [7:0] tap_value278;reg [31:0] pattern278;
 reg [15:0] tap_crc_mask278;
 wire [15:0] tap_address278=startpos+{8'd0,address[7:0]}-16'd16;
 wire [12:0] tap_end278={1'b0,startpos[11:0]}+{1'b0,outlen[11:0]};
 wire tap_capture278=state==NORMAL&&!invalidate_banks&&!tap_seen278&&
  !read_n&&write_n&&bus_valid&&address[23:8]==16'h4000&&address[7:0]>=16;
 wire tap_raw278=tap_pos278>=3169;
 wire [12:0] tap_relative278=tap_pos278-13'd3169;
 wire tap_start278=tap_state278==1;
 wire tap_byte278=tap_state278==2;
 wire tap_idle278=tap_state278==0;
 wire [1:0] pattern_index278=(tap_pos278-startpos)&(header[0]==8?2'd3:2'd1);
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin
   tap_seen278<=0;tap_fault278<=0;tap_repeat278<=0;tap_state278<=0;
   tap_pos278<=0;tap_value278<=0;pattern278<=0;tap_crc_mask278<=0;
  end else if(rst)begin tap_seen278<=0;tap_repeat278<=0;tap_state278<=0;end
  else begin
   if(read_n)tap_seen278<=0;
   if(crc_done278)tap_crc_mask278[crc_index278]<=1;
   if(state==CHECK)begin
    if(!tap_idle278)tap_fault278<=1;
    pattern278<=0;tap_crc_mask278<=0;tap_seen278<=0;
   end
   if(tap_capture278)begin
    tap_seen278<=1;
    if(address[7:0]<20)pattern278[(address[1:0])*8+:8]<=qdata;
    if(data_command278&&header[1]==5)begin
     if(header[0]==2)begin
      if(tap_address278<scroll_length||(prelude_raw!=0&&tap_address278>=3169))begin
       if(!tap_idle278)tap_fault278<=1;
       else begin
        tap_pos278<=tap_address278[12:0];tap_value278<=qdata;
        tap_repeat278<=0;
        tap_state278<=(tap_address278==0||(tap_address278>=3169&&(tap_address278-3169)%16==0))?1:2;
       end
      end
     end else if({8'd0,address[7:0]}==16+plen-1)begin
      if(!tap_idle278)tap_fault278<=1;
      else begin tap_repeat278<=1;tap_pos278<=startpos[12:0];tap_state278<=4;end
     end
    end
   end
   case(tap_state278)
    1:if(range_ready)tap_state278<=2;
    2:if(ordinary_hash_ready)tap_state278<=3;
    3:if(range_ready||ordinary_hash_ready)begin
     if(tap_repeat278)begin tap_pos278<=tap_pos278+1'b1;tap_state278<=4;end
     else tap_state278<=0;
    end
    4:begin
     if(tap_pos278>=tap_end278)begin tap_state278<=0;tap_repeat278<=0;end
     else if(tap_pos278>=scroll_length&&tap_pos278<3169)
      tap_pos278<=(prelude_raw!=0&&tap_end278>3169)?13'd3169:tap_end278;
     else if(tap_pos278>=3169&&prelude_raw==0)tap_pos278<=tap_end278;
     else begin
      tap_value278<=pattern278[pattern_index278*8+:8];
      tap_state278<=(tap_pos278==0||(tap_raw278&&tap_relative278[3:0]==0))?1:2;
     end
    end
    default:begin end
   endcase
  end
 end
 wire consumer_event=''')
    s=once(s,'assign fault=failed||qfault||tfault;', 'assign fault=failed||qfault||tfault||tap_fault278;')
    s=once(s,'assign ordinary_byte=md[7:0];',
           'assign ordinary_byte=tap_byte278?tap_value278:md[7:0];')
    s=once(s,'assign ordinary_hash_start=consumer_event&&consumer_kind==4&&consumer_ready&&!rst;',
           'assign ordinary_hash_start=(tap_start278&&range_ready||consumer_event&&consumer_kind==4&&consumer_ready)&&!rst;')
    s=once(s,'assign ordinary_hash_kind=md[1:0];assign ordinary_hash_index=md[5:2];',
           "assign ordinary_hash_kind=tap_start278?(tap_raw278?2'd0:2'd1):md[1:0];assign ordinary_hash_index=tap_start278?tap_relative278[7:4]:md[5:2];")
    s=once(s,'assign ordinary_hash_byte=consumer_event&&consumer_kind==5&&!rst;',
           'assign ordinary_hash_byte=(tap_byte278||consumer_event&&consumer_kind==5)&&!rst;')
    s=once(s,"if({header[13],header[12]}+16'd16!={7'd0,qlen})failed<=1;",
           "if({header[13],header[12]}+16'd16!={7'd0,qlen}||(data_command278&&bad_data278))failed<=1;")
    s=once(s,'ACKWAIT:if(qdone)begin', 'ACKWAIT:if(qdone&&tap_idle278&&range_ready)begin')
    # Token pattern is latched from the SAME original SNES reads.
    s=once(s,'parser_address<=16;at<=0;state<=OTREAD;',
           'if(pattern278!=token)failed<=1;else state<=OTILE;')
    # No original ordinary payload re-read remains. Internal manifest and
    # H2 retain their single sequential host read, never a SNES copy.
    s=once(s,"if(opos==0)event264(4,18'd1,3'd2);else state<=ODATA;",
           'opos<=scroll_length;')
    s=once(s,"else if(hoff[3:0]==0)event264(4,{12'd0,hoff[7:4],2'd0},3'd2);\n      else state<=ODATA;",
           '''else if(!tap_crc_mask278[hoff[7:4]])failed<=1;
      else begin
       opos<=opos+(hoff[7:4]==15?12'd9:12'd16);
       event264(1,{6'd1,(12'd1312+{8'd0,hoff[7:4]})},3'd1);
      end''')
    a=s.index('     ODATA:begin');b=s.index('     ORLE:begin',a)
    s=s[:a]+s[b:]
    # Invariant guard catches an accidental later regression to byte rereads.
    s=once(s,'     PREAD:state<=PCAP;', '''     PREAD:begin
      if(ordinary_mode&&(data_command278||header[0]==7))failed<=1;
      else state<=PCAP;
     end
''')
    return s


def patch(d):
    p=d/'nes_core257.sv';original=p.read_text()
    p.write_text(source(original),encoding='utf-8',newline='\n')
    (d/'nes_validator278.sv').write_text(validator(original),encoding='utf-8',newline='\n')
    p=d/'nes_mux260.sv';p.write_text(local_flow(tap_flow(p.read_text())),encoding='utf-8',newline='\n')
    p=d/'nes_queue260.sv';p.write_text(queue(p.read_text()),encoding='utf-8',newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text()
    s=once(s,'module nes_joint257(', 'module nes_joint257(output wire [2:0] source_raw278,\n'+ports(GRANT,'input')+ports(RET,'output'))
    s=once(s,'always @(posedge clk)begin bq<=', 'always @(posedge host_clk)begin bq<=')
    s=once(s,' wire [3:0] cf,qf;', ' wire [3:0] cf,qf,vf278;')
    s=once(s,'discovered=cf?cf:', 'discovered=vf278?vf278:cf?cf:')
    s=once(s,'assign start_ready=csr&&!fault;', '''reg [1:0] init_sync278;
 always @(posedge clk or posedge reset)if(reset)init_sync278<=0;else init_sync278<={init_sync278[0],init278};
 assign start_ready=csr&&!fault&&init_sync278[1];''')
    a=s.index('nes_core257 encoder(');b=s.index('nes_transport257 transport(',a)
    inst=s[a:b]
    inst=once(inst,'nes_core257 encoder(', 'nes_core257 encoder(.source_raw278(source_raw278),')
    # Source outputs no longer drive any host validator signal.
    outputs=['display_request_ready','display_response_valid','display_response','ram_b_addr','ram_b_we','ram_b_w',
             'v_ready','h_ready','context_ready','stream_ready','sink_valid','sink_data','sink_kind','sink_unit','sink_lane']
    for n in outputs:inst=re.sub(r'\.'+n+r'\([^)]*\)',f'.{n}()',inst)
    inst=inst.replace('.v_sealed(sealed_raw)', '.v_sealed()').replace('.ram_b_q(ram_b_q)',".ram_b_q(8'd0)")
    validators=['display_write','display_request','display_request_ready','display_response_valid',
                'display_response_ready','display_response','v_begin_valid','v_target_bank','v_raw_count',
                'v_range_valid','v_map_range','v_first','v_count','v_check_valid','v_check_value',
                'v_finish_valid','v_all_consumed','v_ready','h_start','h_kind','h_index','h_valid','h_data',
                'h_ready','context_valid','context_data','context_ready']
    val='nes_validator278 validator('+binds(GRANT+RET)+''.join(f'.{n}({n}),' for n in validators)+'''
 .clk(host_clk),.reset(reset),.abort_source(cancel),.fault(vf278),.v_sealed(sealed_raw),
 .ram_q(ram_b_q),.ram_addr(ram_b_addr),.ram_we(ram_b_we),.ram_w(ram_b_w));
'''
    s=s[:a]+inst+val+'''assign stream_ready=0;assign sink_valid=0;assign sink_data=0;
 assign sink_kind=0;assign sink_unit=0;assign sink_lane=0;
'''+s[b:]
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' wire display_write,','wire [2:0] source_raw278;\n'+ports(GRANT+RET,'wire').replace('wire wire','wire')+' wire display_write,')
    # declarations above need semicolons instead of port commas
    a=s.index('wire grant278,');b=s.index(' wire display_write,',a)
    s=s[:a]+s[a:b].replace(',\n',';\n')+s[b:]
    s=once(s,' flow(', ' flow('+binds(GRANT+RET)+'.epoch278(content_epoch),.raw278(source_raw278),')
    s=once(s,'.identity_valid(identity_valid)', '.identity_valid(identity_valid&&output_phase)')
    s=once(s,'nes_joint257 core(', 'nes_joint257 core(.source_raw278(source_raw278),'+binds(GRANT+RET))
    p.write_text(s,encoding='utf-8',newline='\n')
