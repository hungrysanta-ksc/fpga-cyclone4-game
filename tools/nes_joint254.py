# SPDX-License-Identifier: MIT
"""Bounded FSM extraction diagnostic and query/context consolidation candidate."""
import re
import nes_joint253 as prior
from nes_delta231 import once


def phase_decode(s):
    states=re.search(r'typedef enum logic\[5:0\] \{(.*?)\} state_t;',s,re.S).group(1).split(',')
    names=[n.strip() for n in states if n.strip().startswith(('V_','H_'))]
    return once(s,'assign output_phase=state>=V_CLEARALL;',
                'assign output_phase='+'||'.join('state=='+n for n in names)+';')


def sources(variant='fsm'):
    src=prior.sources()
    src['nes_core253.sv']=phase_decode(src['nes_core253.sv'])
    if variant=='joint':
        src['nes_core253.sv']=consolidate(src['nes_core253.sv'])
        src['nes_joint253.sv']=joint_top(src['nes_joint253.sv'])
        del src['nes_query253.sv']
    return {n.replace('253','254'):s.replace('253','254') for n,s in src.items()}


def consolidate(s):
    # The source cursor owns query location and byte consumption. There is no
    # independent query state, output offset, generation or patch snapshot.
    s=once(s,'WAITACK,V_CLEARALL','WAITACK,Q_WAIT,Q_LOAD,V_CLEARALL')
    s=once(s,'H_HASHBYTE,H_CERT}', 'H_HASHBYTE,H_CERT,H_CERTREAD,H_LENLOREAD,H_LENLO,H_LENHIREAD,H_LENHI}')
    s=once(s,' input wire in_valid,output wire in_ready,input wire [7:0] in_data,input wire [12:0] in_offset,', '''
 input wire [7:0] row_count,object_count,exception_count,input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,
 output wire in_valid,in_ready,output wire [7:0] in_data,output wire [12:0] in_offset,''')
    s=once(s,' input wire [10:0] h_scroll_length,input wire [23:0] h_table_lengths,\n input wire [31:0] h_display_base,input wire [7:0] h_mask,',
           ' input wire context_valid,input wire [7:0] context_data,output wire context_ready,')
    s=once(s,' reg [10:0] h_count,scroll_length;\n reg [23:0] table_lengths;reg [31:0] display_base;reg [7:0] hdma_mask;',
           ' reg [10:0] h_count;reg context_complete,display_less;')
    a=s.index(' wire [15:0] covered=');b=s.index(' wire changed=',a)
    s=s[:a]+QUERY_DECL+CONTEXT_DECL+s[b:]
    # Explicit membership permits Quartus to encode the state machine.
    a=s.index(' assign output_phase=');b=s.index(';',a)
    s=s[:a]+' assign output_phase='+ '||'.join('state=='+n.strip() for n in re.search(r'typedef enum logic\[5:0\] \{(.*?)\} state_t;',s,re.S).group(1).split(',') if n.strip().startswith(('V_','H_')))+s[b:]
    s=s.replace('state==H_BYTES||state==H_SCROLL||state==H_CERT','state==H_BYTES||state==H_SCROLL')
    s=s.replace('assign in_ready=live&&state==FETCH;', 'assign in_ready=in_valid;')
    s=once(s," assign ram_b_addr={1'b1,b_addr};assign ram_b_we=b_we&&!output_phase;assign ram_b_w=b_w;", '''
 wire [9:0] context_addr;wire context_write;
 assign ram_b_addr=output_phase?context_addr:{1'b1,b_addr};
 assign ram_b_we=output_phase?context_write:b_we;assign ram_b_w=output_phase?context_data:b_w;''')
    s=s.replace('(state==H_HASHBYTE?ram_a_q:h_data)', '(state==H_HASHBYTE?ram_a_q:state==H_CERT?ram_b_q:h_data)')
    s=s.replace('scroll_length<=0;table_lengths<=0;display_base<=0;hdma_mask<=0;',
                'context_complete<=0;display_less<=0;'+QUERY_RESET)
    s=s.replace('if(!frame_owned||!geometry_valid||content_epoch==0',
                'if(row_count!=224||!group_count||group_count>32||object_count>128||exception_count>128||!palette_count||palette_count>2||!frame_owned||!geometry_valid||content_epoch==0')
    s=s.replace('admitted_raw<=patch_count;epoch<=content_epoch;', QUERY_START+'admitted_raw<=patch_count;epoch<=content_epoch;')
    a=s.index('    FETCH:');b=s.index('    FSTORE:',a)
    s=s[:a]+QUERY_CASES+s[b:]
    s=s.replace('FSTORE:begin\n     cursor', "FSTORE:begin\n     q_held<={8'd0,q_held[63:8]};\n     cursor")
    s=s.replace('done<=1;state<=V_IDLE;', 'done<=1;rec_i<=0;context_complete<=0;display_less<=0;state<=V_IDLE;')
    a=s.index('    V_IDLE:');b=s.index('    V_CLEARFRAME:',a)
    s=s[:a]+CONTEXT_CASE+s[b:]
    s=s.replace('h_count<=0;checksum<=16\'hffff;digest_ready<=0;state<=H_SCROLL;', "h_count<=0;checksum<=16'hffff;digest_ready<=0;state<=H_LENLOREAD;")
    s=s.replace("h_count<=0;checksum<=16'hffff;state<=H_CERT;", "h_count<=0;checksum<=16'hffff;state<=H_CERTREAD;")
    s=s.replace('if(h_count+1==scroll_length)', 'if(h_count==1)')
    s=s.replace("end else h_count<=h_count+1'b1;\n    end\n    H_HASHREAD", "end else h_count<=h_count-1'b1;\n    end\n    H_HASHREAD")
    a=s.index('    H_CERT:');b=s.index('    default:begin fault<=6;',a)
    s=s[:a]+CERT_CASES+'\n'+s[b:]
    return s


def joint_top(s):
    s=once(s,'input wire [10:0] h_scroll_length,\ninput wire [23:0] h_table_lengths,\ninput wire [31:0] h_display_base,\ninput wire [7:0] h_mask,',
           'input wire context_valid,\ninput wire [7:0] context_data,\noutput wire context_ready,')
    s=s.replace('cf?cf:qf?qf:sf||hf?', 'cf?cf:sf||hf?')
    s=s.replace('csr&&qsr&&!fault','csr&&!fault')
    a=s.index(' assign query=');b=s.index('nes_core253 encoder',a)
    s=s[:a]+s[b:]
    a=s.index('nes_query253 reader');b=s.index('nes_transport253 transport',a)
    s=s[:a]+s[b:]
    old='.h_scroll_length(h_scroll_length),.h_table_lengths(h_table_lengths),.h_display_base(h_display_base),.h_mask(h_mask)'
    s=once(s,old,'.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready)')
    more=['row_count','object_count','exception_count','group_count','palette_count','query','query_kind','query_index','query_generation']
    return once(s,'nes_core253 encoder(', 'nes_core253 encoder('+','.join('.'+n+'('+n+')' for n in more)+',')


QUERY_DECL=r'''
 reg [10:0] q_maps;reg [7:0] q_objects,q_exceptions;reg [6:0] q_palettes;
 reg [7:0] q_mode;reg q_normal;reg [2:0] q_raw_seen;reg [63:0] q_held;
 reg [2:0] q_section;reg [10:0] q_index;reg q_first,q_active;
 reg [7:0] q_value;reg [15:0] q_tail;wire [12:0] q_rel=cursor-13'd4385;
 always @*begin
  q_section=0;q_index=0;q_first=1;q_active=0;q_value=q_held[7:0];q_tail=0;
  if(cursor<2112)begin q_section=0;q_index=cursor[11:1];q_first=!cursor[0];q_active=q_index<q_maps;end
  else if(cursor<2336)begin q_section=1;q_index=cursor-2112;q_active=1;end
  else if(cursor<3360)begin q_section=2;q_index=(cursor-2336)>>3;q_first=cursor[2:0]==0;q_active=q_index<q_objects;end
  else if(cursor<3872)begin q_section=3;q_index=(cursor-3360)>>2;q_first=cursor[1:0]==0;q_active=q_index<q_exceptions;end
  else if(cursor<4320)begin q_section=4;q_index=(cursor-3872)>>1;q_first=!cursor[0];q_active=1;end
  else if(cursor==4320)begin q_value=q_mode;q_first=0;end
  else if(cursor<4385)begin q_section=5;q_index=cursor-4321;q_active=q_index<q_palettes;end
  else begin
   q_first=0;
   case(q_rel[3:1])
    0:q_tail={5'd0,q_maps};1,4:q_tail=224;
    2:q_tail={8'd0,q_objects};3:q_tail={8'd0,q_exceptions};5:q_tail={9'd0,q_palettes};default:q_tail=0;
   endcase
   q_value=q_rel==12?{5'd0,admitted_raw}:q_rel[0]?q_tail[15:8]:q_tail[7:0];
  end
 end
 assign query=raw_query||(live&&state==FETCH&&q_first&&q_active);
 assign query_kind=raw_query?3'd7:q_section;assign query_index=raw_query?raw_index:{2'd0,q_index};
 assign query_generation=generation;
 assign in_valid=live&&(state==Q_LOAD||(state==FETCH&&!q_first));
 assign in_offset=cursor;assign in_data=q_value;
'''
QUERY_RESET='q_maps<=0;q_objects<=0;q_exceptions<=0;q_palettes<=0;q_mode<=0;q_normal<=0;q_raw_seen<=0;q_held<=0;'
QUERY_START="q_maps<={group_count,5'd0}+group_count;q_objects<=object_count;q_exceptions<=exception_count;q_palettes<=palette_count==1?32:64;q_mode<=0;q_normal<=0;q_raw_seen<=0;"
QUERY_CASES=r'''
    FETCH:begin
     if(cursor>=4398||(cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))begin fault<=3;base_valid<=0;end
     else if(!q_first)begin new_byte<=q_value;state<=FSTORE;end
     else if(q_active)state<=Q_WAIT;
     else begin q_held<=0;state<=Q_LOAD;end
    end
    Q_LOAD:begin new_byte<=q_value;state<=FSTORE;end
    Q_WAIT:if(raw_response)begin
     if(!raw_hit||(q_section==0&&raw_data[63:15]!=0)||(q_section==1&&raw_data[63:8]!=0)||
        (q_section==3&&raw_data[63:32]!=0)||(q_section==5&&raw_data[63:6]!=0))fault<=3;
     else if(q_section==4)begin
      if(raw_data[49])begin
       if(raw_data[63:53]!=0||raw_data[48:0]!=0||raw_data[52:50]!=q_raw_seen||q_raw_seen>=admitted_raw)fault<=3;
       else begin q_held<={50'd0,raw_data[52:50],1'b1,10'd0};q_raw_seen<=q_raw_seen+1'b1;state<=Q_LOAD;end
      end else if(raw_data[63:49]!=0||(raw_data[43:36]!=8'h18&&raw_data[43:36]!=8'h1e)||
                  (q_normal&&raw_data[43:36]!=q_mode)||raw_data[48:44]>=(q_palettes==32?2'd1:2'd2))fault<=3;
      else begin q_held<={54'd0,raw_data[44],raw_data[32:30],raw_data[10],raw_data[4:0]};q_normal<=1;q_mode<=raw_data[43:36];state<=Q_LOAD;end
     end else begin q_held<=raw_data;state<=Q_LOAD;end
    end
'''
CONTEXT_DECL=r'''
 // Same 32 certificate bytes are staged once, before output admission. Source
 // scratch has retired; no additional wire copy or context latch is assumed.
 assign context_ready=!reset&&!abort_source&&!fault&&lease_ok&&state==V_IDLE&&!context_complete;
 assign context_write=context_ready&&context_valid;
 assign context_addr=state==V_IDLE?10'd832+{2'd0,rec_i}:
     (state==H_LENLOREAD||state==H_LENLO)?10'd846:
     (state==H_LENHIREAD||state==H_LENHI)?10'd847:10'd832+{5'd0,h_count[4:0]};
 wire [15:0] context_covered={5'd0,h_count}+(admitted_raw?16'd249:16'd0);
 reg [7:0] context_expected,serial_byte;reg context_bad;
 always @*begin
  context_expected=0;serial_byte=0;context_bad=0;
  case(rec_i)
   0:context_expected="H";1:context_expected="2";2:context_expected=2;3:context_expected={7'd0,~base_serial[0]};
   4:context_expected=epoch[7:0];5:context_expected=epoch[15:8];6:context_expected=epoch[23:16];7:context_expected=epoch[31:24];
   8:context_expected=base_serial[7:0];9:context_expected=base_serial[15:8];10:context_expected=base_serial[23:16];11:context_expected=base_serial[31:24];
   12:context_expected=generation[7:0];13:context_expected=generation[15:8];
   20:context_expected={5'd0,admitted_raw};21:context_expected=0;
   24:context_expected=context_covered[7:0];25:context_expected=context_covered[15:8];
   default:begin end
  endcase
  case(rec_i[1:0])
   2:serial_byte=base_serial[7:0];3:serial_byte=base_serial[15:8];0:serial_byte=base_serial[23:16];1:serial_byte=base_serial[31:24];
  endcase
  if(rec_i<14||rec_i==20||rec_i==21||rec_i==24||rec_i==25)context_bad=context_data!=context_expected;
  if(rec_i==15)context_bad=context_data>4||{context_data,h_count[7:0]}==0||{context_data,h_count[7:0]}>1121;
  if(rec_i>=16&&rec_i<=18)context_bad=admitted_raw?(context_data==0||context_data>81):context_data!=0;
  if(rec_i==19)context_bad=context_data!=8'h18&&context_data!=8'h1e;
 end
'''
CONTEXT_CASE=r'''
    V_IDLE:begin
     if(context_write)begin
      if(context_bad)fault<=7;
      if(rec_i==14)h_count<={3'd0,context_data};
      if(rec_i==15)h_count<={context_data[2:0],h_count[7:0]};
      if(rec_i>=26&&rec_i<=29)display_less<=context_data<serial_byte||(context_data==serial_byte&&display_less);
      if(rec_i==31)context_complete<=1;else rec_i<=rec_i+1'b1;
     end
     if(v_begin_valid)begin
      if(!context_complete||!display_less||v_target_bank!=~base_serial[0]||v_raw_count!=admitted_raw)fault<=7;
      else begin v_bank<=v_target_bank;certificate_ok<=0;digest_ready<=0;v_raw<=v_raw_count;v_cursor<=396;v_check_index<=0;v_map_end<=0;seal_state<=0;state<=V_CLEARFRAME;end
     end
    end
'''
CERT_CASES=r'''
    H_LENLOREAD:state<=H_LENLO;
    H_LENLO:begin h_count<={3'd0,ram_b_q};state<=H_LENHIREAD;end
    H_LENHIREAD:state<=H_LENHI;
    H_LENHI:begin h_count<={ram_b_q[2:0],h_count[7:0]};state<=H_SCROLL;end
    H_CERTREAD:state<=H_CERT;
    H_CERT:begin
     if((h_count==22&&ram_b_q!=digest[7:0])||(h_count==23&&ram_b_q!=digest[15:8])||
        (h_count==30&&ram_b_q!=checksum[7:0])||(h_count==31&&ram_b_q!=checksum[15:8]))fault<=7;
     else begin
      if(h_count<30)checksum<=crc_result;
      if(h_count==31)begin certificate_ok<=1;state<=V_ACTIVE;end
      else begin h_count<=h_count+1'b1;state<=H_CERTREAD;end
     end
    end
'''
