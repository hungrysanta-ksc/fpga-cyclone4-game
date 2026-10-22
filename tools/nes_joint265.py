# SPDX-License-Identifier: MIT
"""Replace duplicate queue ACK/header state; consume manifests internally.

Keep the existing ACK identity bytes, compare them in order against the admitted
identity, and retire only after direct payload validation. Display context is
retained explicitly (24 bytes), read once after sealing, and covered by final ACK.
"""
from nes_joint264 import sources as prior
from nes_delta231 import once


def sources():
 src=prior();s=src['nes_queue260.sv']
 s=s.replace(' output reg ack_done,\n','')
 s=once(s,' input wire ack_write,input wire [3:0] ack_index,input wire [7:0] ack_byte,\n input wire ack_publish,output reg fault',' output reg fault')
 a=s.index(' reg [95:0] ack_work;');b=s.index(' reg [7:0] read_data;',a);s=s[:a]+s[b:]
 s=once(s,"wire [7:0] read_address=checking?{4'd0,check_index}:sn_address;",'wire [7:0] read_address=sn_address;')
 s=s.replace('used!=0&&!checking&&enable','used!=0&&enable').replace("full,ack_valid,", "full,1'b0,")
 s=once(s,'   ack_done<=0;accepted<=0;retired<=0;ack_work<=0;ack_mask<=0;ack_valid<=0;fault<=0;\n   checking<=0;check_wait<=0;check_index<=0;', '   accepted<=0;retired<=0;fault<=0;')
 s=once(s,'   ack_done<=0;\n','')
 a=s.index('   if(parser_retire');b=s.index('   if(!ss[1]',a)
 s=s[:a]+'''   if(parser_retire&&enable&&!fault)begin
    if(!packet_ready)fault<=1;else retired<=retired+1'b1;
   end
'''+s[b:]
 s=s.replace('// Every SNES ACK is checked against the head packet BEFORE releasing credit.', '// Admission/ordered ACK identity is owned by the flow; only parser_retire releases credit.')
 src['nes_queue260.sv']=s
 s=src['nes_mux260.sv']
 s=once(s,'.ack_write(ack_write),.ack_index(ap[3:0]),.ack_byte(dp),.ack_publish(ack_publish),.parser_retire(qretire),.ack_done(qdone),.fault(qfault)', '.parser_retire(qretire),.fault(qfault)')
 s=once(s,' wire [7:0] qaddr=', ''' // Shared identity expectation: header admission and ordered ACK use it.
 function automatic [7:0] identity_byte(input [3:0] i);
  case(i)
   2:identity_byte=packet_seq[7:0];3:identity_byte=packet_seq[15:8];
   4:identity_byte=identity[7:0];5:identity_byte=identity[15:8];
   6:identity_byte=identity[23:16];7:identity_byte=identity[31:24];
   8:identity_byte=identity[39:32];9:identity_byte=identity[47:40];
   default:identity_byte=0;
  endcase
 endfunction
 wire [7:0] ack_expected=ap[3:0]==0?8'd0:ap[3:0]==1?header[0]:
   ap[3:0]==10?8'h65:ap[3:0]==11?8'h9a:identity_byte(ap[3:0]);
 assign qdone=state==ACKWAIT&&!fault&&!rst;
 reg [7:0] display_context[0:23];
 wire display_address=address>=24'h006070&&address<24'h006088;
 wire display_read=ap>=24'h006070&&ap<24'h006088;
 wire [7:0] qaddr=''')
 s=once(s,'HCAP:begin header[at]<=qdata;', '''HCAP:begin
      if(at>=2&&at<=9)begin if(qdata!=identity_byte(at[3:0]))failed<=1;end
      else header[at]<=qdata;''')
 s=once(s,"||{header[3],header[2]}!=packet_seq||packet_seq==16'hffff||\n       {header[7],header[6],header[5],header[4]}!=identity[31:0]||{header[9],header[8]}!=identity[47:32]", "||packet_seq==16'hffff")
 s=s.replace('ordinary_reads<=0;tile_proven<=0;state<=NORMAL;', 'ordinary_reads<=0;tile_proven<=0;at<=0;state<=NORMAL;')
 s=once(s,'      else if(header[0]!=12)begin', '''      else if(header[0]==15||header[0]==10||header[0]==11||header[0]==3)begin
       if(plen+16'd16!={7'd0,qlen})failed<=1;else state<=OSETUP;
      end
      else if(header[0]!=12)begin''')
 s=once(s,"     if(ap==24'h00601c)begin if(!ack_publish||ordinary_reads!=qlen||(header[0]==7&&!tile_proven))failed<=1;else state<=ACKWAIT;end", '''     if(ack_write)begin
      if(at>=12||ap[3:0]!=at[3:0]||dp!=ack_expected)failed<=1;
      else at<=at+1'b1;
     end
     if(ap==24'h00601c)begin if(!ack_publish||at!=12||ordinary_reads!=qlen||(header[0]==7&&!tile_proven))failed<=1;else state<=ACKWAIT;end''')
 s=once(s,'    if(consume)read_count<=0;', '''    if(rs&&!rp&&display_read)begin
     if(state!=IDLE||manifest_phase!=2||!sealed_sync[1]||at>=24||ap!=24'h006070+at)failed<=1;
     else at<=at+1'b1;
    end
    if(consume)read_count<=0;''')
 s=once(s,"||!sealed_sync[1]||dp!=8'h5a", "||!sealed_sync[1]||at!=24||dp!=8'h5a")
 s=once(s,"assign data_out=address[23:8]==16'h0060 ? control", "assign data_out=display_address ? display_context[address-24'h006070] : address[23:8]==16'h0060 ? control")
 s=once(s,"((address[23:8]==16'h0060)||", "((address[23:8]==16'h0060&&(!display_address||(state==IDLE&&sealed_sync[1]&&manifest_phase==2)))||")
 s=once(s,'manifest_phase<=1;opos<=40;oend<=206;state<=OREAD;parser_address<=40;', 'manifest_phase<=1;opos<=16;oend<=206;state<=OREAD;parser_address<=16;')
 s=once(s,"else if(header[0]==15)begin opos<=opos+1'b1;parser_address<=parser_address+1'b1;event264(3,{10'd0,qdata},OCHECKNEXT);end", '''else if(header[0]==15)begin
       opos<=opos+1'b1;parser_address<=parser_address+1'b1;
       if(opos<40)begin display_context[opos-16]<=qdata;state<=PREAD;end
       else event264(3,{10'd0,qdata},OCHECKNEXT);
      end''')
 s=once(s,"ORET:begin ordinary_mode<=0;qretire<=1;", "ORET:begin if(header[0]==3)at<=0;ordinary_mode<=0;qretire<=1;")
 # Continuations are a compact operation selector, not a second copy of state.
 # All FSM next states are now constants; this is part of replacing parser control.
 targets=['OTILE','OSELECT','ODATA','OCHECKNEXT','ORLE','OCERT','OFINISH','ORET']
 s=s.replace('reg [5:0] after_event;', 'reg [2:0] event_return;')
 s=s.replace('input [5:0] continuation', 'input [2:0] continuation').replace('after_event<=continuation','event_return<=continuation').replace('after_event<=0','event_return<=0')
 import re
 for i,target in enumerate(targets):s=re.sub(r'(event264\([^;\n]*,)'+target+r'(\);)',lambda m:m[1]+f"3'd{i}"+m[2],s)
 s=once(s,'OWAIT:if(mready)state<=after_event;', 'OWAIT:if(mready)case(event_return)\n'+''.join(f"      3'd{i}:state<={t};\n" for i,t in enumerate(targets))+'     endcase')
 src['nes_mux260.sv']=s
 src['nes_joint265.sv']=src.pop('nes_joint264.sv').replace('nes_joint264','nes_joint265')
 return src
