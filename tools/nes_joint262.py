# SPDX-License-Identifier: MIT
"""H2 ingress shares the existing queue reader/held byte with map staging.

BEGIN remains an ordinary SNES-owned packet. Its checked ordinary ACK triggers
the core BEGIN through the same 9-bit CDC mailbox used for H2 bytes. The SNES
BEGIN payload checks and all other ordinary producers are explicit boundaries.
"""
from nes_joint261 import sources as prior
from nes_delta231 import once


def sources(shared=True):
 src=prior();s=src['nes_mux260.sv']
 s=once(s,'output wire ordinary_ready,output wire [31:0] next_token',
 '''output wire context_valid,output wire [7:0] context_data,input wire context_ready,
 output wire begin_valid,output wire begin_bank,output wire [2:0] begin_raw,
 output wire ordinary_ready,output wire [31:0] next_token''')
 s=once(s,'BRET=20;','BRET=20,PREWAIT=21,BSTART=22,BWAIT=23;')
 s=once(s,'reg batch;','reg prelude_mode,prelude_done,begun;reg [2:0] prelude_raw;\n reg batch;')
 s=once(s,' genvar k;', '''
 wire pv,pr,ps;wire [8:0] pd;
 nes_native_mailbox206 #(.WIDTH(9)) prelude(.src_clk(host_clk),.dst_clk(nes_clk),.reset(rst),
 .src_valid((prelude_mode&&state==PUT)||state==BSTART),.src_ready(ps),
 .src_data(state==BSTART?{1'b1,4'd0,prelude_raw,identity[48]}:{1'b0,held}),
 .dst_valid(pv),.dst_ready(pr),.dst_data(pd));
 assign context_valid=pv&&!pd[8]&&!rst;assign context_data=pd[7:0];
 assign begin_valid=pv&&pd[8]&&range_ready&&!rst;
 assign begin_bank=pd[0];assign begin_raw=pd[3:1];
 assign pr=pd[8]?range_ready:context_ready;
 genvar k;
''')
 s=once(s,'wire mput=state==PUT&&owner==MAP;','wire mput=state==PUT&&owner==MAP&&!prelude_mode;')
 s=once(s,'batch<=0;remaining<=0;', 'prelude_mode<=0;prelude_done<=0;begun<=0;prelude_raw<=0;batch<=0;remaining<=0;')
 s=once(s,'identity<=idata;have_identity<=1;', 'identity<=idata;have_identity<=1;prelude_done<=0;begun<=0;prelude_mode<=0;')
 s=once(s,'      else if(header[0]==14)begin', '''      else if(header[0]==13)begin
       if(prelude_done||begun||qlen!=48||header[1]!=5||{header[13],header[12]}!=32||
          {header[11],header[10]}!=0||{header[15],header[14]}!=0)failed<=1;
       else begin prelude_mode<=1;length<=32;at<=0;parser_address<=16;state<=PREAD;end
      end
      else if(!prelude_done||(header[0]==1?begun:!begun))failed<=1;
      else if(header[0]==1)begin
       if(qlen!=28||header[1]!=0||{header[13],header[12]}!=12||
          {header[11],header[10]}!=0||{header[15],header[14]}!=0)failed<=1;
       else state<=NORMAL;
      end
      else if(header[0]==14)begin''')
 s=once(s,'PUT:if(put_ready)begin if(at+1==length)state<=SEAL;', '''PUT:if(prelude_mode?ps:put_ready)begin
      if(prelude_mode&&at==20)prelude_raw<=held[2:0];
      if(at+1==length)state<=prelude_mode?PREWAIT:SEAL;''')
 s=once(s,'     BRET:state<=IDLE;', '''     PREWAIT:if(ps)begin
      prelude_mode<=0;prelude_done<=1;qretire<=1;packet_seq<=packet_seq+1'b1;state<=BRET;
     end
     BSTART:if(ps)state<=BWAIT;
     BWAIT:if(ps)begin begun<=1;state<=IDLE;end
     BRET:state<=IDLE;''')
 s=once(s,'ACKWAIT:if(qdone)begin packet_seq<=packet_seq+1\'b1;state<=IDLE;end',
 "ACKWAIT:if(qdone)begin packet_seq<=packet_seq+1'b1;state<=header[0]==1?BSTART:IDLE;end")
 if shared:
  # The existing24-bit map-consumption mailbox has unused bit23: map first
  # is at most2047. Reuse it for context/BEGIN in disjoint parser phases.
  start=s.index(' wire pv,pr,ps;');end=s.index(' genvar k;',start)
  s=s[:start]+s[end:]
  s=once(s,'.src_valid(state==SEND),.src_ready(mready),.src_data({first,count}),.dst_valid(mv),.dst_ready(ns==3),.dst_data(md));',
   '''.src_valid(state==SEND||(prelude_mode&&state==PUT)||state==BSTART),.src_ready(mready),
 .src_data(state==SEND?{first,count}:state==BSTART?{2'b11,18'd0,prelude_raw,identity[48]}:{2'b10,14'd0,held}),
 .dst_valid(mv),.dst_ready(md[23]?(md[22]?range_ready:context_ready):ns==3),.dst_data(md));
 assign context_valid=mv&&md[23]&&!md[22]&&!rst;assign context_data=md[7:0];
 assign begin_valid=mv&&md[23]&&md[22]&&range_ready&&!rst;
 assign begin_bank=md[0];assign begin_raw=md[3:1];''')
  s=once(s,'range_valid=mv&&ns==0', 'range_valid=mv&&!md[23]&&ns==0')
  s=once(s,'0:if(mv&&range_ready)', '0:if(mv&&!md[23]&&range_ready)')
  s=s.replace('prelude_mode?ps:put_ready','prelude_mode?mready:put_ready').replace('PREWAIT:if(ps)','PREWAIT:if(mready)').replace('BSTART:if(ps)','BSTART:if(mready)').replace('BWAIT:if(ps)','BWAIT:if(mready)')
 src['nes_mux260.sv']=s
 s=src.pop('nes_joint261.sv').replace('nes_joint261','nes_joint262')
 for decl in ['input wire  v_begin_valid,','input wire  v_target_bank,','input wire [2:0] v_raw_count,',
              'input wire  context_valid,','input wire [7:0] context_data,']:
  s=once(s,decl,'')
 s=once(s,' wire [15:0] display_generation;', ''' wire v_begin_valid,v_target_bank,context_valid;wire [2:0] v_raw_count;wire [7:0] context_data;
 wire [15:0] display_generation;''')
 s=once(s,'.receipt_committed(receipt_committed),.fault(flow_fault),', '''.receipt_committed(receipt_committed),.fault(flow_fault),
 .context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),
 .begin_valid(v_begin_valid),.begin_bank(v_target_bank),.begin_raw(v_raw_count),''')
 src['nes_joint262.sv']=s
 return src
