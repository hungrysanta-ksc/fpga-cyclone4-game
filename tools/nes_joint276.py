# SPDX-License-Identifier: MIT
"""Original consumed descriptor, one source/query/receipt execution FSM.

The host retains queue admission, SNES reads/ACK and typed map staging. Its
ordinary interpreter is removed. The existing24bit/8bit CDC pair transports
eight descriptor words and requested payload bytes, without another RAM.
Source/query registers are reused only after source commit. No reference
program is transmitted and no independent NES parser FSM remains.
"""
import re
from nes_delta231 import ROOT,once
from nes_joint272 import parser,flow as host_flow

PORT_CORE='''input wire desc_valid276,desc_byte276,input wire [15:0] desc_data276,
 output wire desc_ready276,reply_valid276,output wire [7:0] reply_data276,input wire reply_ready276,
'''
PORT_FLOW='''output wire desc_valid276,desc_byte276,output wire [15:0] desc_data276,
 input wire desc_ready276,reply_valid276,input wire [7:0] reply_data276,output wire reply_ready276,
'''
BIND=''.join(f'.{n}({n}),' for n in (
 'desc_valid276','desc_byte276','desc_data276','desc_ready276',
 'reply_valid276','reply_data276','reply_ready276'))
STATES=['LOAD','OSETUP','OTILE','OSELECT','ODATA','READREQ','PCAP','ORLE',
        'OCHECKNEXT','OCERT','OFINISH','ORET','RETURN','RECV']


def queue(s):
 s=once(s,'payload_size,request_crc,received_crc','request_crc')
 s=once(s," wire [16:0] expected_length={1'b0,payload_size}+17'd16;",'')
 s=s.replace('payload_size<=0;','').replace('received_crc<=0;','')
 s=once(s,'payload_size>240||byte_count!=expected_length+3||bit_count!=0||received_crc!=request_crc',
        'byte_count<19||byte_count>259||bit_count!=0||request_crc!=0')
 s=once(s,'expected_length[8:0]',"byte_count-9'd3")
 a=s.index('      if(byte_count==13)payload_size');b=s.index('\n     end',a)
 return s[:a]+'''      request_crc<=crc16(request_crc,incoming);
      if(can_write&&byte_count<=256)buffer[{accepted[1:0],8'd0}+byte_count-1'b1]<=incoming;
'''+s[b:]


def flow(s):
 s=host_flow(s)
 s=once(s,'(\n input wire [48:0] link270','(\n '+PORT_FLOW+' input wire [48:0] link270')
 a=s.index(' wire parser_word_ready,');b=s.index(' wire legacy_event=',a)
 s=s[:a]+''' wire parser_word=mv&&md[23:22]==2'b10&&(md[21:18]==9||md[21:18]==10);
 assign desc_valid276=parser_word;assign desc_byte276=md[21:18]==10;
 assign desc_data276=md[15:0];
 assign reply_ready276=back_ready&&!display_response_valid&&ns!=3;
'''+s[b:]
 s=s.replace('wire consumer_event=legacy_event||parser_event_valid;', 'wire consumer_event=legacy_event;')
 s=s.replace('parser_event_valid?parser_kind:md[21:18]','md[21:18]')
 s=s.replace('parser_event_valid?parser_data:md[17:0]','md[17:0]')
 s=s.replace(' assign parser_event_ready=consumer_ready;\n','')
 for a,b in [('parser_word_ready','desc_ready276'),('parser_reply_valid','reply_valid276'),('parser_reply','reply_data276')]:
  s=s.replace(a,b)
 return s


def core(s,original_flow):
 # Borrow only the already checked ordinary semantics, not the272 parser
 # registers, always block, event mailbox or state machine.
 p=parser(original_flow)
 a=p.index('    PCAP:begin');b=p.index('    default:failed<=1;',a)
 body=p[a:b]
 a=body.index('     OISSUE:');b=body.index('     OCERT:',a)
 body=body[:a]+body[b:]
 body=body.replace('failed<=1','fault<=7')
 body=body.replace('     ORET:state<=RETURN;', '     ORET:state<=RETURN;')
 # One original DMA range issues up to16 granules per core receipt request.
 body=body.replace("opos<=opos+1'b1;event264(1,{6'd1,opos},3'd0);",
                   "opos<=opos+tile_take276;event264(1,{tile_take276,opos[11:0]},3'd0);")
 body=body.replace("opos<=opos+16;event264(1,{6'd1,(12'd1152+{4'd0,opos[11:4]})},3'd1);",
                   "opos<=opos+({7'd0,range_take276}<<4);event264(1,{range_take276,(12'd1152+{4'd0,opos[11:4]})},3'd1);")
 body=body.replace("opos<=opos+16;event264(1,{6'd1,(12'd1184+{4'd0,boff[11:4]})},3'd1);",
                   "opos<=opos+({7'd0,tail_take276}<<4);event264(1,{tail_take276,(12'd1184+{4'd0,boff[11:4]})},3'd1);")
 # Source-only register lvalues. Core cursor/expanded/build_i remain owned
 # by receipt, CRC and display routines and cannot alias the parser.
 aliases={'opos':'raw_at','oend':'raw_limit','parser_address':'mask_acc',
  'qdata':'new_byte','rle_left':'raw_count','rle_zero':'shift_left',
  'manifest_at':'spans','manifest_phase':'q_mode[1:0]','at':'diff_count'}
 for a,b in aliases.items():body=re.sub(r'\b'+a+r'\b',b,body)
 for name in STATES:body=re.sub(r'\b'+name+r'\b','P_'+name,body)
 body=re.sub(r'\bevent264\b','execute276',body)
 s=once(s,'module nes_core257(', 'module nes_core257(\n '+PORT_CORE)
 s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,'+','.join('P_'+x for x in STATES)+'} state_t;')
 # Exact equality keeps Quartus FSM extraction (254 finding).
 pphase='||'.join('state==P_'+x for x in STATES)
 s=once(s,' assign output_phase=', ' wire descriptor_phase276='+pphase+';\n assign output_phase=descriptor_phase276||')
 s=once(s,' assign v_ready=!reset', ' assign v_ready=!left_row&&!reset')
 s=once(s,'state<=V_IDLE;end\n    end\n    V_CLEARALL:',
          'left_row<=0;q_normal<=0;state<=V_IDLE;end\n    end\n    V_CLEARALL:')
 s=once(s,'rec_i<=0;v_bank<=v_target_bank;', 'spans<=0;q_mode<=0;left_row<=0;q_normal<=0;rec_i<=0;v_bank<=v_target_bank;')
 # Only this same FSM touches the aliased source/context fields.
 decl=''' wire [7:0] header[0:15];
 assign {header[15],header[14],header[13],header[12],header[11],header[10],header[1],header[0]}=q_held;
 wire [8:0] qlen={edge1[0],edge0};wire tile_proven=edge1[1];
 wire [31:0] token={new2,new1,old2,old1};
 wire [10:0] scroll_length=q_maps;wire [2:0] prelude_raw=q_raw_seen;
 wire [15:0] plen={header[13],header[12]},startpos={header[11],header[10]};
 wire [15:0] outlen=header[0]==2?plen:{header[15],header[14]};
 wire [11:0] hoff=raw_at-13'd3169,boff=raw_at-13'd1121;
 wire [12:0] range_left276=raw_limit-raw_at;
 wire [12:0] tail_left276=(raw_limit<3169?raw_limit:13'd3169)-raw_at;
 wire [5:0] tile_take276=range_left276>16?6'd16:range_left276[5:0];
 wire [5:0] range_take276=range_left276>256?6'd16:range_left276[9:4];
 wire [5:0] tail_take276=tail_left276>256?6'd16:tail_left276[9:4];
 wire [17:0] local_data276={q_palettes[1:0],q_exceptions,q_objects};
 wire [3:0] local_kind276=block_id[3:0];
 wire local_event276=left_row&&q_normal;
 state_t resume276;
 always @*case(record_length[2:0])
  0:resume276=P_OTILE;1:resume276=P_OSELECT;2:resume276=P_ODATA;3:resume276=P_OCHECKNEXT;
  4:resume276=P_ORLE;5:resume276=P_OCERT;6:resume276=P_OFINISH;7:resume276=P_ORET;
 endcase
 assign desc_ready276=!reset&&!abort_source&&!fault&&lease_ok&&!q_pending&&
  ((state==V_ACTIVE&&!left_row)||state==P_LOAD||state==P_RECV);
 assign reply_valid276=!reset&&!abort_source&&!fault&&lease_ok&&(state==P_READREQ||state==P_RETURN);
 assign reply_data276=state==P_RETURN?8'd0:mask_acc;
 task load276(input [2:0] i,input [15:0] value);
 begin
  case(i)
   0:q_held[15:0]<=value;1:q_held[31:16]<=value;
   2:q_held[47:32]<=value;3:q_held[63:48]<=value;
   4:begin edge0<=value[7:0];edge1[1:0]<=value[9:8];end
   5:begin old1<=value[7:0];old2<=value[15:8];end
   6:begin new1<=value[7:0];new2<=value[15:8];end
   7:begin q_maps<=value[10:0];q_raw_seen<=value[13:11];end
  endcase
 end endtask
 task execute276(input [3:0] k,input [17:0] value,input [2:0] continuation);
 begin
  block_id[3:0]<=k;{q_palettes[1:0],q_exceptions,q_objects}<=value;
  record_length[2:0]<=continuation;q_normal<=1;
  if(k==5)state<=right_row?H_SCROLL:H_BYTES;
  else begin if(k==4&&value[1:0]<2)right_row<=value[0];state<=V_ACTIVE;end
 end endtask
'''
 s=once(s,' wire crc_output=output_phase;', decl+'\n wire crc_output=output_phase;')
 # Existing handlers service local requests directly, retaining receipt/CRC
 # bounds. Local ordinary DMA is already consumed before descriptor admission.
 a=s.index('    V_ACTIVE:begin');b=s.index('    V_STREAM:',a)
 active=s[a:b]
 names={'display_write':'(display_write||(local_event276&&local_kind276==7))',
 'h_start':'(h_start||(local_event276&&local_kind276==4))',
 'h_kind':'(local_event276?local_data276[1:0]:h_kind)',
 'h_index':'(local_event276?local_data276[5:2]:h_index)',
 'v_range_valid':'(v_range_valid||(local_event276&&local_kind276==1))',
 'v_first':'(local_event276?local_data276[11:0]:v_first)',
 'v_count':"(local_event276?{6'd0,local_data276[17:12]}:v_count)",
 'v_map_range':"(local_event276?1'b0:v_map_range)",
 'v_check_valid':'(v_check_valid||(local_event276&&local_kind276==3))',
 'v_check_value':'(local_event276?local_data276[7:0]:v_check_value)',
 'v_finish_valid':'(v_finish_valid||(local_event276&&local_kind276==6))'}
 for n in sorted(names,key=len,reverse=True):active=re.sub(r'\b'+n+r'\b',names[n],active)
 active=active.replace('    V_ACTIVE:begin','''    V_ACTIVE:begin
     if(local_event276)q_normal<=0;
     if(desc_valid276&&desc_ready276)begin
      if(desc_byte276)fault<=7;
      else begin left_row<=1;row_i<=1;load276(0,desc_data276);state<=P_LOAD;end
     end else if(left_row&&!q_normal)state<=resume276;
     else''')
 active=active.replace('state<=V_STREAM;', 'state<=local_event276?V_RREAD:V_STREAM;')
 active=active.replace('state<=H_BYTES;', 'state<=local_event276?resume276:H_BYTES;')
 active=active.replace('state<=V_WAITDISPLAY;', 'state<=local_event276?P_RETURN:V_WAITDISPLAY;')
 s=s[:a]+active+s[b:]
 # Local byte event uses the same CRC combinational datapath.
 s=once(s,'state==H_CERT?ram_b_q:h_data', 'state==H_CERT?ram_b_q:local_event276?local_data276[7:0]:h_data')
 s=once(s,'H_BYTES:if(h_valid)begin','H_BYTES:if(h_valid||local_event276)begin\n     if(local_event276)q_normal<=0;')
 s=once(s,"else hash_lane<=hash_lane+1'b1;", "else begin hash_lane<=hash_lane+1'b1;if(local_event276)state<=resume276;end")
 s=once(s,'H_SCROLL:if(h_valid)begin','H_SCROLL:if(h_valid||local_event276)begin\n     if(local_event276)q_normal<=0;')
 s=once(s,"else h_count<=h_count-1'b1;", "else begin h_count<=h_count-1'b1;if(local_event276)state<=resume276;end")
 s=once(s,'state<=H_SCROLL;end\n    H_CERTREAD:', 'state<=left_row?resume276:H_SCROLL;end\n    H_CERTREAD:')
 tail='''    P_LOAD:if(desc_valid276&&desc_ready276)begin
     if(desc_byte276)fault<=7;
     else begin load276(row_i[2:0],desc_data276);row_i<=row_i+1'b1;if(row_i==7)state<=P_OSETUP;end
    end
    P_READREQ:if(reply_ready276)begin
     if(mask_acc<16||{1'b0,mask_acc}>=qlen)fault<=7;else state<=P_RECV;
    end
    P_RECV:if(desc_valid276&&desc_ready276)begin
     if(!desc_byte276)fault<=7;else begin new_byte<=desc_data276[7:0];state<=P_PCAP;end
    end
    P_RETURN:if(reply_ready276)begin left_row<=0;q_normal<=0;state<=seal_state?V_WAITDISPLAY:V_ACTIVE;end
'''+body
 # Earlier range/hash wait assertions still reject premature external input.
 s=once(s,'    default:begin fault<=6;base_valid<=0;end',tail+'\n    default:begin fault<=6;base_valid<=0;end')
 return s


def patch(d):
 p=d/'nes_mux260.sv';original=p.read_text();p.write_text(flow(original),encoding='utf-8',newline='\n')
 p=d/'nes_core257.sv';p.write_text(core(p.read_text(),original),encoding='utf-8',newline='\n')
 p=d/'nes_queue260.sv';p.write_text(queue(p.read_text()),encoding='utf-8',newline='\n')
 p=d/'nes_joint257.sv';s=p.read_text()
 s=once(s,'module nes_joint257(', 'module nes_joint257(\n '+PORT_CORE)
 s=once(s,'nes_core257 encoder(', 'nes_core257 encoder('+BIND)
 p.write_text(s,encoding='utf-8',newline='\n')
 p=d/'nes_joint266.sv';s=p.read_text()
 s=once(s,' wire display_write,',''' wire desc_valid276,desc_byte276,desc_ready276,reply_valid276,reply_ready276;
 wire [15:0] desc_data276;wire [7:0] reply_data276;
 wire display_write,''')
 s=once(s,' flow(', ' flow('+BIND)
 s=once(s,'nes_joint257 core(', 'nes_joint257 core('+BIND)
 p.write_text(s,encoding='utf-8',newline='\n')
