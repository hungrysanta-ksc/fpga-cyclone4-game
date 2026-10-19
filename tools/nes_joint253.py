# SPDX-License-Identifier: MIT
"""Experimental fused source/receipt control and phase-owned CRC shadow RAM.

The output port represents bytes CONSUMED by the destination adapter. It is
not an implementation of that adapter, the SNES acknowledgement, or ARM RUN.
"""
import re
from nes_delta231 import BASE, once
from nes_phase251 import sources as phase_sources


def core():
    old=phase_sources()
    s=old['nes_source_phase251.sv']
    v=old['nes_receipt_phase251.sv']
    # Move the receipt arrays above the persistent 64-byte shadow.
    v=v.replace("10'd332","10'd396").replace("10'd498","10'd562")
    v=v.replace('cursor<=332','cursor<=396').replace('cursor==753','cursor==817')
    # One state register, one fault, one reset/STOP lifetime. No second FSM.
    states=re.search(r'localparam (.*?);',v,re.S).group(1)
    state_names=re.findall(r'(\w+)=\d+',states)
    for name in sorted(state_names,key=len,reverse=True):
        v=re.sub(r'\b'+name+r'\b','V_'+name,v)
    # Rename receipt-local declarations, preserving only the shared controls.
    names=['bank','mapmode','raw','cursor','check_index','addr','wdata','mask','value',
           'bit_at','left','map_end','take','initialized','we','validbase','available',
           'ntake','lowmask','nextmask','ready','sealed','begin_valid','target_bank',
           'raw_count','range_valid','map_range','first','count','check_valid',
           'check_value','finish_valid','all_consumed','display_ack','q']
    for name in sorted(names,key=len,reverse=True):
        v=re.sub(r'\b'+name+r'\b','v_'+name,v)
    declarations=v[v.index(' reg bank') if ' reg bank' in v else v.index('reg [3:0] state;'):v.index(' task advance_range;')]
    declarations=declarations.replace('reg [3:0] state;','')
    declarations=declarations.replace('wire live=!reset&&!abort_source&&!fault;','')
    declarations=declarations.replace('wire [7:0] v_q=ram_q;','wire [7:0] v_q=ram_a_q;')
    declarations=declarations.replace(' assign ram_addr=v_addr;assign ram_we=v_we;assign ram_wdata=v_wdata;','')
    tasks=v[v.index(' task advance_range;'):v.index(' always @(posedge clk)begin')]
    reset=re.search(r'if\(reset\)begin (.*?)end\n  else if',v,re.S).group(1)
    reset=reset.replace('state<=V_CLEARALL;','').replace('fault<=0;','')
    cases=v[v.index('    V_CLEARALL:'):v.index('    default:fault<=6;')]
    cases=cases.replace('state<=V_IDLE','state<=IDLE')
    # V_IDLE is the post-input-commit output admission state.
    cases=cases.replace('V_CLEARALL:if(v_cursor==817)state<=IDLE;', 'V_CLEARALL:if(v_cursor==817)state<=IDLE;')
    cases=cases.replace('if(v_check_index!=422||!v_all_consumed)',
                        'if(v_check_index!=422||!v_all_consumed||!certificate_ok)')
    cases=cases.replace("(v_map_range?13'd2048:13'd1328)", "(v_map_range?13'd2048:13'd1312)")
    cases=cases.replace('v_sealed<=0;state<=IDLE;', 'v_sealed<=0;state<=IDLE;')
    cases=cases.replace('v_bank<=v_target_bank;', 'v_bank<=v_target_bank;certificate_ok<=0;digest_ready<=0;')
    # Host identity remains held from the actual source admission.
    cases=cases.replace('V_IDLE:if(v_begin_valid)begin', '''V_IDLE:if(v_begin_valid)begin
     if(v_target_bank!=~base_serial[0]||v_raw_count!=admitted_raw||
        h_scroll_length==0||h_scroll_length>1121||h_display_base>=base_serial||
        (h_mask!=8'h18&&h_mask!=8'h1e)||
        (v_raw_count!=0&&(h_table_lengths[7:0]==0||h_table_lengths[7:0]>81||
         h_table_lengths[15:8]==0||h_table_lengths[15:8]>81||h_table_lengths[23:16]==0||h_table_lengths[23:16]>81)))fault<=7;
     scroll_length<=h_scroll_length;table_lengths<=h_table_lengths;
     display_base<=h_display_base;hdma_mask<=h_mask;''')
    cases=cases.replace('else if(v_range_valid)begin', '''else if(h_start)begin
      if(h_kind==0&&v_check_index==0&&v_raw!=0)begin
       hash_index<=h_index;hash_lane<=0;work_crc<=16'hffff;state<=H_BYTES;
      end else if(h_kind==1&&v_check_index==422)begin
       h_count<=0;work_crc<=16'hffff;digest_ready<=0;state<=H_SCROLL;
      end else if(h_kind==2&&digest_ready&&!certificate_ok)begin
       h_count<=0;work_crc<=16'hffff;state<=H_CERT;
      end else fault<=7;
     end else if(v_range_valid)begin''')
    # Extend source's single FSM, retaining its immutable publication latch.
    s=s.replace('module nes_source_phase251','module nes_core253')
    extra_states=','.join('V_'+n for n in state_names)+',H_BYTES,H_WRITELO,H_WRITEHI,H_SCROLL,H_HASHREAD,H_HASHBYTE,H_CERT'
    s=s.replace('typedef enum logic[4:0]', 'typedef enum logic[5:0]',1)
    s=once(s,'ENDTRAILER,WAITACK}', 'ENDTRAILER,WAITACK,'+extra_states+'}')
    s=once(s,' input wire clk,reset,abort_source,',PORTS+'\n input wire clk,reset,abort_source,')
    s=once(s,' input wire [7:0] ram_a_q,ram_b_q,output wire [8:0] ram_a_addr,ram_b_addr,',
           ' input wire [7:0] ram_a_q,ram_b_q,output wire [9:0] ram_a_addr,ram_b_addr,')
    s=once(s,' assign ram_a_addr=a_addr;assign ram_a_we=a_we;assign ram_a_w=a_w;',
           " assign ram_a_addr=output_phase?v_addr:{1'b1,a_addr};assign ram_a_we=output_phase?v_we:a_we;assign ram_a_w=output_phase?v_wdata:a_w;")
    s=once(s,' assign ram_b_addr=b_addr;assign ram_b_we=b_we;assign ram_b_w=b_w;',
           " assign ram_b_addr={1'b1,b_addr};assign ram_b_we=b_we&&!output_phase;assign ram_b_w=b_w;")
    s=once(s,' wire live;',DECLARATIONS+'\n wire live;')
    s=once(s,' assign live=!reset&&!abort_source&&!fault&&lease_ok;',
           ' assign live=!reset&&!abort_source&&!fault&&lease_ok&&!output_phase;')
    declarations=declarations.replace('if(!live)v_we=0;', 'if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;')
    declarations=declarations.replace('assign v_ready=live&&','assign v_ready=!reset&&!abort_source&&!fault&&lease_ok&&')
    declarations=declarations.replace('   default:begin end',HASH_RAM+'\n   default:begin end')
    s=once(s,' task automatic emit_record',declarations+'\n'+tasks+'\n task automatic emit_record')
    s=once(s,'state<=IDLE;kind<=H;', 'state<=V_CLEARALL;'+reset+HASH_RESET+'kind<=H;')
    s=once(s,'else if(state!=IDLE&&!lease_ok)', 'else if(state!=IDLE&&state!=V_CLEARALL&&!lease_ok)')
    s=s.replace('assign ack_ready=live&&state==WAITACK;', 'assign ack_ready=live&&state==WAITACK&&transport_empty;')
    s=s.replace('WAITACK:if(ack_valid)begin','WAITACK:if(ack_valid&&ack_ready)begin')
    s=s.replace('fault<=4;base_valid<=0;', 'if(!fault)fault<=4;base_valid<=0;v_sealed<=0;')
    s=once(s,'else if(!fault&&ack_valid&&state!=WAITACK&&state!=IDLE)',
           'else if(!fault&&ack_valid&&!output_phase&&state!=WAITACK&&state!=IDLE)')
    s=once(s,'else if(!fault)case(state)',
           'else if(!fault&&v_display_ack&&state!=V_WAITDISPLAY)begin fault<=5;v_sealed<=0;end\n   else if(!fault)case(state)')
    s=once(s,'epoch<=content_epoch;', 'admitted_raw<=patch_count;epoch<=content_epoch;')
    s=s.replace('if(!frame_owned||!geometry_valid||frame_serial==0', 'if(!frame_owned||!geometry_valid||content_epoch==0||frame_serial==0')
    s=once(s,'done<=1;state<=IDLE;', 'done<=1;state<=V_IDLE;')
    s=once(s,'    default:begin fault<=6;',cases+HASH_CASES+'\n    default:begin fault<=6;')
    # Source, block transport and output verifier use one combinational CRC16.
    s=s.replace('checksum<=crc16(checksum,byte_data)', 'checksum<=crc_result')
    s=once(s,' reg [7:0] header_byte,out_byte;',CRC+'\n reg [7:0] header_byte,out_byte;')
    a=s.index('reg v_bank,');b=s.index(' wire [9:0] v_validbase',a)
    early=s[a:b];s=s[:a]+s[b:];s=s.replace(' state_t state;kind_t kind;', ' state_t state;kind_t kind;\n'+early)
    a=s.index(' assign output_phase=');b=s.index(' wire live;',a)
    late=s[a:b];s=s[:a]+s[b:];s=s.replace(' wire changed=',late+'\n wire changed=')
    head,body=s.split(');',1)
    head=head.replace('output reg v_sealed','output wire v_sealed')
    body=re.sub(r'\bv_sealed\b','seal_state',body)
    body=body.replace(' state_t state;', ' reg seal_state;\n state_t state;')
    body=body.replace(' assign live=', ' assign v_sealed=seal_state&&!reset&&!abort_source&&!fault&&lease_ok;\n assign live=')
    # Input stream CRC is dead after COMMITTED; reuse that register for every
    # output digest/certificate operation. Block CRC remains live concurrently
    # with input stream CRC and must retain its independent state.
    body=body.replace('reg [15:0] work_crc,digest;', 'reg [15:0] digest;')
    body=body.replace("work_crc<=16'hffff;digest<=0;", 'digest<=0;')
    body=re.sub(r'\bwork_crc\b','checksum',body)
    body=body.replace('wire live;', 'wire live,lease_ok;').replace('wire lease_ok=', 'assign lease_ok=')
    s=head+');'+body
    return s


PORTS=r'''
 input wire v_begin_valid,v_target_bank,input wire [2:0] v_raw_count,
 input wire v_range_valid,v_map_range,input wire [11:0] v_first,v_count,
 input wire v_check_valid,input wire [7:0] v_check_value,
 input wire v_finish_valid,v_all_consumed,v_display_ack,
 output wire v_ready,output reg v_sealed,
 input wire h_start,input wire [1:0] h_kind,input wire [3:0] h_index,
 input wire h_valid,input wire [7:0] h_data,output wire h_ready,
 input wire [10:0] h_scroll_length,input wire [23:0] h_table_lengths,
 input wire [31:0] h_display_base,input wire [7:0] h_mask,
 input wire transport_crc_pending,transport_empty,input wire [15:0] transport_crc,
 input wire [7:0] transport_byte,output wire [15:0] crc_result,
 output wire output_phase,
'''
DECLARATIONS=r'''
 reg [2:0] admitted_raw;
 reg [3:0] hash_index,hash_lane;
 reg [10:0] h_count,scroll_length;
 reg [23:0] table_lengths;reg [31:0] display_base;reg [7:0] hdma_mask;
 reg [15:0] work_crc,digest;
 reg certificate_ok,digest_ready;
 assign output_phase=state>=V_CLEARALL;
 assign h_ready=!reset&&!abort_source&&!fault&&lease_ok&&(state==H_BYTES||state==H_SCROLL||state==H_CERT);
 wire [9:0] hash_base=10'd332+{4'd0,v_bank,5'd0};
 wire [15:0] covered={5'd0,scroll_length}+(v_raw?16'd249:16'd0);
 reg [7:0] cert_expected;
 always @*begin
  case(h_count)
   0:cert_expected="H";1:cert_expected="2";2:cert_expected=2;3:cert_expected={7'd0,v_bank};
   4:cert_expected=epoch[7:0];5:cert_expected=epoch[15:8];6:cert_expected=epoch[23:16];7:cert_expected=epoch[31:24];
   8:cert_expected=base_serial[7:0];9:cert_expected=base_serial[15:8];10:cert_expected=base_serial[23:16];11:cert_expected=base_serial[31:24];
   12:cert_expected=generation[7:0];13:cert_expected=generation[15:8];14:cert_expected=scroll_length[7:0];15:cert_expected={5'd0,scroll_length[10:8]};
   16:cert_expected=v_raw?table_lengths[7:0]:0;17:cert_expected=v_raw?table_lengths[15:8]:0;18:cert_expected=v_raw?table_lengths[23:16]:0;
   19:cert_expected=hdma_mask;20:cert_expected={5'd0,v_raw};21:cert_expected=0;
   22:cert_expected=digest[7:0];23:cert_expected=digest[15:8];24:cert_expected=covered[7:0];25:cert_expected=covered[15:8];
   26:cert_expected=display_base[7:0];27:cert_expected=display_base[15:8];28:cert_expected=display_base[23:16];29:cert_expected=display_base[31:24];
   30:cert_expected=work_crc[7:0];31:cert_expected=work_crc[15:8];default:cert_expected=0;
  endcase
 end
'''
CRC=r'''
 wire crc_output=output_phase;
 wire [15:0] crc_previous=crc_output?work_crc:transport_crc_pending?transport_crc:checksum;
 wire [7:0] crc_byte=crc_output?(state==H_HASHBYTE?ram_a_q:h_data):transport_crc_pending?transport_byte:byte_data;
 assign crc_result=crc16(crc_previous,crc_byte);
'''
HASH_RESET="admitted_raw<=0;hash_index<=0;hash_lane<=0;h_count<=0;scroll_length<=0;table_lengths<=0;display_base<=0;hdma_mask<=0;work_crc<=16'hffff;digest<=0;certificate_ok<=0;digest_ready<=0;"
HASH_RAM=r'''
   H_WRITELO,H_WRITEHI:begin
    v_addr=hash_base+{5'd0,hash_index,1'b0}+(state==H_WRITEHI?10'd1:10'd0);
    v_we=1;v_wdata=state==H_WRITELO?work_crc[7:0]:work_crc[15:8];
   end
   H_HASHREAD,H_HASHBYTE:v_addr=hash_base+{5'd0,h_count[4:0]};
'''
HASH_CASES=r'''
    H_BYTES:if(h_valid)begin
     work_crc<=crc_result;
     if(hash_lane==(hash_index==15?8:15))state<=H_WRITELO;
     else hash_lane<=hash_lane+1'b1;
    end
    H_WRITELO:state<=H_WRITEHI;
    H_WRITEHI:begin v_bit_at<=12'd1312+{8'd0,hash_index};v_left<=1;v_mapmode<=0;state<=V_RREAD;end
    H_SCROLL:if(h_valid)begin
     work_crc<=crc_result;
     if(h_count+1==scroll_length)begin
      h_count<=0;
      if(v_raw)state<=H_HASHREAD;else begin digest<=crc_result;digest_ready<=1;state<=V_ACTIVE;end
     end else h_count<=h_count+1'b1;
    end
    H_HASHREAD:state<=H_HASHBYTE;
    H_HASHBYTE:begin
     work_crc<=crc_result;
     if(h_count==31)begin digest<=crc_result;digest_ready<=1;state<=V_ACTIVE;end
     else begin h_count<=h_count+1'b1;state<=H_HASHREAD;end
    end
    H_CERT:if(h_valid)begin
     if(h_data!=cert_expected)fault<=7;
     else begin
      if(h_count<30)work_crc<=crc_result;
      if(h_count==31)begin certificate_ok<=1;state<=V_ACTIVE;end
      else h_count<=h_count+1'b1;
     end
    end
'''


def transport():
    s=(BASE/'probes/nes-source240/board01/nes_source_spi235.sv').read_text()
    s=s.replace('nes_source_spi235','nes_transport253')
    s=s.replace(' output wire source_fault,host_fault',' output wire source_fault,host_fault,source_empty')
    s=s.replace(' wire room=', ' assign source_empty=source_live&&!busy&&!remaining&&!used&&!crc_pending;\n wire room=')
    s=once(s,' input wire src_clk,host_clk,reset,abort_source,', '''
 input wire [15:0] crc_result,output reg crc_pending,
 output wire [15:0] crc_previous,output reg [7:0] crc_byte,
 input wire src_clk,host_clk,reset,abort_source,''')
    a=s.index(' function automatic [15:0] c16');b=s.index(' function automatic [7:0] c8',a)
    s=s[:a]+s[b:]
    s=s.replace('wire room=', 'assign crc_previous=block_crc;\n wire room=')
    s=s.replace('assign record_ready=source_live&&','assign record_ready=source_live&&!crc_pending&&')
    s=s.replace('assign byte_ready=source_live&&','assign byte_ready=source_live&&!crc_pending&&')
    s=s.replace('block_crc<=16\'hffff;descriptor0', "crc_pending<=0;crc_byte<=0;block_crc<=16'hffff;descriptor0")
    s=s.replace('if(record_valid&&!remaining&&!busy[bank])','if(record_valid&&!remaining&&!busy[bank]&&!crc_pending)')
    s=once(s,"     remaining<=remaining-1'b1;used<=used+1'b1;block_crc<=c16(block_crc,byte_data);\n     if(remaining==1&&(flush_record||used==247))seal(used+1'b1,c16(block_crc,byte_data));", '''
     remaining<=remaining-1'b1;used<=used+1'b1;crc_pending<=1;crc_byte<=byte_data;
    end
    if(crc_pending)begin
     crc_pending<=0;block_crc<=crc_result;
     if(remaining==0&&(flush_record||used==248))seal(used,crc_result);''')
    return s


def sources():
    return {'nes_core253.sv':core(),'nes_transport253.sv':transport(),
            'nes_query253.sv':query(), 'nes_joint253.sv':top()}


def query():
    s=(BASE/'probes/nes-source240/board01/nes_source_query235.sv').read_text()
    s=s.replace('nes_source_query235','nes_query253')
    s=s.replace('TAIL=4;', 'TAIL=4,MODE=5;')
    s=s.replace(' reg [15:0] generation;', ' reg [7:0] mode;reg normal_seen;reg [2:0] raw_seen;\n reg [15:0] generation;')
    s=s.replace('state==EMIT||state==TAIL','state==EMIT||state==TAIL||state==MODE')
    s=s.replace('4:begin limit=224;capacity=224;width=8;', '4:begin limit=224;capacity=224;width=2;')
    s=s.replace('assign out_data=state==TAIL?', 'assign out_data=state==MODE?mode:state==TAIL?')
    s=s.replace('generation<=0;held<=0;', 'mode<=0;normal_seen<=0;raw_seen<=0;generation<=0;held<=0;')
    s=s.replace('generation<=frame_generation;map_count', 'mode<=0;normal_seen<=0;raw_seen<=0;generation<=frame_generation;map_count')
    s=s.replace('else begin held<=data;state<=EMIT;end', '''else if(section==4)begin
      if(data[49])begin
       if(data[63:53]!=0||data[48:0]!=0||data[52:50]!=raw_seen||raw_seen>=patches)fault<=3;
       else begin held<={50'd0,data[52:50],1'b1,10'd0};raw_seen<=raw_seen+1'b1;state<=EMIT;end
      end else if(data[63:49]!=0||(data[43:36]!=8'h18&&data[43:36]!=8'h1e)||
                  (normal_seen&&data[43:36]!=mode)||data[48:44]>=(palettes==32?2'd1:2'd2))fault<=3;
      else begin held<={54'd0,data[44],data[32:30],data[10],data[4:0]};normal_seen<=1;mode<=data[43:36];state<=EMIT;end
     end else begin held<=data;state<=EMIT;end''')
    s=s.replace('if(section==5)state<=TAIL;else begin section<=section+1\'b1;state<=ASK;end',
                "if(section==5)state<=TAIL;else if(section==4)state<=MODE;else begin section<=section+1'b1;state<=ASK;end")
    s=s.replace('    TAIL:if(out_ready)', '''    MODE:if(out_ready)begin
     if(!normal_seen||raw_seen!=patches)fault<=3;
     else begin out_offset<=out_offset+1'b1;section<=5;state<=ASK;end
    end
    TAIL:if(out_ready)''')
    return s


def top():
    s=core()
    h=re.search(r'module nes_core253\((.*?)\);',s,re.S).group(1)
    chunks=h.split(',')
    names=lambda h:[re.search(r'(\w+)\s*$',x).group(1) for x in h.split(',')]
    cn=names(h)
    remove={'ram_a_q','ram_b_q','ram_a_addr','ram_b_addr','ram_a_we','ram_b_we','ram_a_w','ram_b_w',
            'transport_crc_pending','transport_empty','transport_crc','transport_byte','crc_result',
            'in_valid','in_ready','in_data','in_offset','raw_query','raw_index','raw_response','raw_hit','raw_data',
            'record_valid','record_ready','record_length','record_flush','byte_valid','byte_ready','byte_data',
            'ack_valid','ack_ready','ack_accept','ack_generation'}
    # Expand declarations before filtering: comma continuation retains its type.
    ports=[];prefix=''
    for chunk in chunks:
        name=re.search(r'(\w+)\s*$',chunk).group(1)
        head=chunk[:chunk.rfind(name)].strip()
        if head:prefix=head
        if name not in remove:ports.append(prefix.replace('output reg','output wire')+' '+name)
    ports+=['input wire host_clk,SPI_SS,SPI_SCK,SPI_MOSI','output wire selected,miso',
            'input wire [7:0] row_count,object_count,exception_count','input wire [5:0] group_count,palette_count',
            'output wire query','output wire [2:0] query_kind','output wire [12:0] query_index',
            'output wire [15:0] query_generation','input wire response,hit','input wire [63:0] data']
    body=r'''
 wire [7:0] ram_a_q,ram_b_q;wire [9:0] ram_a_addr,ram_b_addr;
 wire ram_a_we,ram_b_we;wire [7:0] ram_a_w,ram_b_w;
 (* ramstyle="M9K" *) reg [7:0] memory[0:1023];reg [7:0] aq,bq;
 assign ram_a_q=aq;assign ram_b_q=bq;
 always @(posedge clk)begin aq<=memory[ram_a_addr];if(ram_a_we&&!fault)memory[ram_a_addr]<=ram_a_w;end
 always @(posedge clk)begin bq<=memory[ram_b_addr];if(ram_b_we&&!fault)memory[ram_b_addr]<=ram_b_w;end
 wire transport_crc_pending,transport_empty;wire [15:0] transport_crc,crc_result;wire [7:0] transport_byte;
 wire in_valid,in_ready;wire [7:0] in_data;wire [12:0] in_offset;
 wire raw_query;wire [12:0] raw_index;
 wire raw_response=response,raw_hit=hit;wire [63:0] raw_data=data;
 wire record_valid,record_ready,record_flush,byte_valid,byte_ready;
 wire [7:0] record_length,byte_data;wire ack_valid,ack_ready,ack_accept;wire [15:0] ack_generation;
 wire csr,qsr,qd,rquery,sf,hf;wire [2:0] rkind;wire [12:0] rindex;wire [15:0] rgen;
 wire [3:0] cf,qf;wire cancel=abort_source||fault!=0;wire sealed_raw;
 wire [3:0] discovered=cf?cf:qf?qf:sf||hf?4'd8:4'd0;
 reg [3:0] first_fault;
 always @(posedge clk)if(reset)first_fault<=0;else if(!first_fault&&discovered)first_fault<=discovered;
 assign fault=first_fault?first_fault:discovered;
 assign v_sealed=sealed_raw&&!fault&&!abort_source&&frame_owned&&geometry_valid&&output_phase;
 assign start_ready=csr&&qsr&&!fault;
 assign query=raw_query||rquery;assign query_kind=raw_query?3'd7:rkind;
 assign query_index=raw_query?raw_index:rindex;assign query_generation=rgen;
'''
    cmap={n:n for n in cn};cmap.update(start='start&&start_ready',start_ready='csr',fault='cf',abort_source='cancel',v_sealed='sealed_raw')
    # Do not make fault->abort->fault a combinational loop: faults are registers.
    body+='nes_core253 encoder('+','.join('.'+n+'('+cmap[n]+')' for n in cn)+');\n'
    qn=names(re.search(r'module nes_query253\((.*?)\);',query(),re.S).group(1))
    qm=dict(start='start&&start_ready',start_ready='qsr',abort_source='cancel',query='rquery',query_kind='rkind',query_index='rindex',query_generation='rgen',out_valid='in_valid',out_ready='in_ready',out_data='in_data',out_offset='in_offset',done='qd',fault='qf')
    body+='nes_query253 reader('+','.join('.'+n+'('+qm.get(n,n)+')' for n in qn)+');\n'
    tn=names(re.search(r'module nes_transport253\((.*?)\);',transport(),re.S).group(1))
    tm=dict(src_clk='clk',abort_source='cancel',crc_pending='transport_crc_pending',crc_previous='transport_crc',crc_byte='transport_byte',source_empty='transport_empty',source_fault='sf',host_fault='hf')
    body+='nes_transport253 transport('+','.join('.'+n+'('+tm.get(n,n)+')' for n in tn)+');\n'
    return 'module nes_joint253('+',\n'.join(ports)+');\n'+body+'endmodule\n'
