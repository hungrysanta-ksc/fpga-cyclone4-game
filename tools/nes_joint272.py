# SPDX-License-Identifier: MIT
"""Move ordinary payload interpretation across the existing mailbox.

First structural slice: host keeps admission, SNES reads/ACK and map staging.
NES parser drives the existing receipt/CRC core locally. The optional shared
variant reuses120 source-register bits; neither variant adds a phase-RAM buffer.
"""
from nes_delta231 import ROOT,once,sha


def parser(s):
    # Preserve the proven semantic rules verbatim; change their byte/event
    # transport, not their interpretation. Identity was admitted on the host.
    setup=s[s.index('     OSETUP:begin'):s.index('\n     default:;',s.index('     OSETUP:begin'))]
    setup=setup[:setup.index('     ORET:')]+'''     ORET:state<=RETURN;
'''
    setup=setup.replace('ordinary_mode<=1;','')
    setup=setup.replace('OREAD','READREQ').replace('OTREAD','READREQ')
    setup=setup.replace('OISSUE:if(mready)','OISSUE:if(event_ready)')
    # Acceptance already occurred in OISSUE. The core can legitimately remain
    # in H_BYTES waiting for the next byte; do not wait for range_ready here.
    setup=setup.replace('OWAIT:if(mready)','OWAIT:')
    body=s[s.index('      if(header[0]==7)begin',s.index('PREAD:state<=PCAP')):s.index('\n     PUT:if(')]
    body=body[:body.rindex('\n     end')]
    body=body.replace('PREAD','READREQ').replace('OREAD','READREQ')
    return '''// SPDX-License-Identifier: MIT
// NES-clock interpreter. One outstanding host RAM read, no packet buffer.
module nes_parser272(
 input wire clk,reset,frame_begin,
 input wire word_valid,word_byte,input wire [15:0] word_data,output wire word_ready,
 output wire reply_valid,output wire [7:0] reply_data,input wire reply_ready,
 output wire event_valid,output wire [3:0] event_kind,output wire [17:0] event_data,
 input wire event_ready
);
 localparam LOAD=0,OSETUP=1,OTILE=2,OSELECT=3,ODATA=4,READREQ=5,PCAP=6,
 ORLE=7,OCHECKNEXT=8,OISSUE=9,OWAIT=10,OCERT=11,OFINISH=12,ORET=13,RETURN=14,RECV=15;
 reg [3:0] state;reg failed;reg [2:0] meta_at;
 reg [7:0] header[0:15],parser_address,at;
 reg [8:0] qlen,manifest_at;reg [1:0] manifest_phase;
 reg [31:0] token;reg tile_proven;reg [10:0] scroll_length;reg [2:0] prelude_raw;
 reg [11:0] opos,oend;reg [7:0] rle_left;reg rle_zero;reg [2:0] event_return;
 reg [23:0] consumer_word;reg [7:0] qdata;
 wire [11:0] hoff=opos-12'd3169,boff=opos-12'd1121;
 wire [15:0] plen={header[13],header[12]},startpos={header[11],header[10]};
 wire [15:0] outlen=header[0]==2?plen:{header[15],header[14]};
 assign word_ready=!reset&&!failed&&(state==LOAD||state==RECV);
 assign reply_valid=!reset&&(failed||state==READREQ||state==RETURN);
 // Legal body addresses are16..255. 0=complete, 1=sticky failure.
 assign reply_data=failed?8'd1:state==RETURN?8'd0:parser_address;
 assign event_valid=!reset&&!failed&&state==OISSUE;
 assign event_kind=consumer_word[21:18];assign event_data=consumer_word[17:0];
 task event264(input [3:0] k,input [17:0] value,input [2:0] continuation);
 begin consumer_word<={2'b10,k,value};event_return<=continuation;state<=OISSUE;end
 endtask
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   state<=LOAD;failed<=0;meta_at<=0;manifest_at<=0;manifest_phase<=0;
   parser_address<=0;at<=0;opos<=0;oend<=0;rle_left<=0;rle_zero<=0;
   consumer_word<=0;event_return<=0;qdata<=0;qlen<=0;token<=0;
   tile_proven<=0;scroll_length<=0;prelude_raw<=0;
  end else if(frame_begin)begin
   if(state!=LOAD||meta_at!=0)failed<=1;
   manifest_at<=0;manifest_phase<=0;
  end else if(!failed)begin
   if(word_valid&&word_ready&&word_byte!=(state==RECV))failed<=1;
   else case(state)
    LOAD:if(word_valid)begin
     case(meta_at)
      0:begin header[0]<=word_data[7:0];header[1]<=word_data[15:8];end
      1:begin header[10]<=word_data[7:0];header[11]<=word_data[15:8];end
      2:begin header[12]<=word_data[7:0];header[13]<=word_data[15:8];end
      3:begin header[14]<=word_data[7:0];header[15]<=word_data[15:8];end
      4:begin qlen<=word_data[8:0];tile_proven<=word_data[9];end
      5:token[15:0]<=word_data;
      6:token[31:16]<=word_data;
      7:begin scroll_length<=word_data[10:0];prelude_raw<=word_data[13:11];end
     endcase
     meta_at<=meta_at+1'b1;if(meta_at==7)state<=OSETUP;
    end
    READREQ:if(reply_ready)begin
     if(parser_address<16||{1'b0,parser_address}>=qlen)failed<=1;
     else state<=RECV;
    end
    RECV:if(word_valid)begin qdata<=word_data[7:0];state<=PCAP;end
    RETURN:if(reply_ready)state<=LOAD;
    PCAP:begin
'''+body+'\n    end\n'+setup+'''
    default:failed<=1;
   endcase
  end
 end
endmodule
'''


def flow(s):
    # Delete the host semantic interpreter and its state/context.
    a=s.index(' reg ordinary_mode;');b=s.index(' wire consumer_event=',a)
    s=s[:a]+''' reg ordinary_mode;reg [8:0] ordinary_reads;
 reg [10:0] scroll_length;reg [1:0] manifest_phase;reg tile_proven;
 wire [15:0] plen={header[13],header[12]};
 localparam OPUSH=40,OMETA=41,OREPLY=42,OBYTE=43,OBWAIT=44;
 reg [15:0] meta272;
 always @*case(at[2:0])
  0:meta272={header[1],header[0]};
  1:meta272={header[11],header[10]};
  2:meta272={header[13],header[12]};
  3:meta272={header[15],header[14]};
  4:meta272={6'd0,tile_proven,qlen};
  5:meta272=token[15:0];
  6:meta272=token[31:16];
  7:meta272={2'd0,prelude_raw,scroll_length};
 endcase
 wire back_ready;
 wire parser_word_ready,parser_reply_valid,parser_event_valid,parser_event_ready;
 wire [7:0] parser_reply;wire [3:0] parser_kind;wire [17:0] parser_data;
 wire parser_word=mv&&md[23:22]==2'b10&&(md[21:18]==9||md[21:18]==10);
 nes_parser272 parser272(.clk(nes_clk),.reset(rst),.frame_begin(begin_valid),
  .word_valid(parser_word),.word_byte(md[21:18]==10),.word_data(md[15:0]),.word_ready(parser_word_ready),
  .reply_valid(parser_reply_valid),.reply_data(parser_reply),.reply_ready(back_ready&&!display_response_valid&&ns!=3),
  .event_valid(parser_event_valid),.event_kind(parser_kind),.event_data(parser_data),.event_ready(parser_event_ready));
''' + s[b:]
    s=s.replace(' reg [23:0] consumer_word;\n','')
    s=once(s,' wire back_ready,bv;', ' wire bv;')
    s=once(s,"wire consumer_event=mv&&md[23:22]==2'b10&&md[21:18]!=0;",
        "wire legacy_event=mv&&md[23:22]==2'b10&&md[21:18]!=0&&!parser_word;\n wire consumer_event=legacy_event||parser_event_valid;")
    s=once(s,'wire [3:0] consumer_kind=md[21:18];',
        'wire [3:0] consumer_kind=parser_event_valid?parser_kind:md[21:18];\n wire [17:0] event_data272=parser_event_valid?parser_data:md[17:0];')
    s=once(s,' assign display_write=', ' assign parser_event_ready=consumer_ready;\n assign display_write=')
    for old,new in [('ordinary_first=md[11:0]','ordinary_first=event_data272[11:0]'),
                    ("ordinary_count={6'd0,md[17:12]}","ordinary_count={6'd0,event_data272[17:12]}"),
                    ('ordinary_byte=md[7:0]','ordinary_byte=event_data272[7:0]'),
                    ('ordinary_hash_kind=md[1:0]','ordinary_hash_kind=event_data272[1:0]'),
                    ('ordinary_hash_index=md[5:2]','ordinary_hash_index=event_data272[5:2]')]:
        s=once(s,old,new)
    s=once(s,'state==DREQ||state==OISSUE||state==SEND','state==DREQ||state==OPUSH||state==OBYTE||state==SEND')
    s=once(s,'state==OISSUE?consumer_word:',"state==OPUSH?{2'b10,4'd9,2'd0,meta272}:state==OBYTE?{2'b10,4'd10,10'd0,held}:")
    s=once(s,'.dst_ready(consumer_event?consumer_ready:', '.dst_ready(parser_word?parser_word_ready:legacy_event?consumer_ready:')
    s=once(s,'.src_valid(ns==3||display_response_valid)', '.src_valid(ns==3||display_response_valid||parser_reply_valid)')
    s=once(s,'.src_data(display_response_valid?display_response:8\'d1)',".src_data(display_response_valid?display_response:ns==3?8'd1:parser_reply)")
    s=once(s,'.dst_ready(state==WAIT_RECEIPT||state==DWAIT)', '.dst_ready(state==WAIT_RECEIPT||state==DWAIT||state==OREPLY)')
    s=once(s,'ordinary_mode<=0;consumer_word<=0;opos<=0;oend<=0;scroll_length<=0;manifest_at<=0;manifest_phase<=0;ordinary_reads<=0;tile_proven<=0;rle_left<=0;rle_zero<=0;event_return<=0;',
        'ordinary_mode<=0;scroll_length<=0;manifest_phase<=0;ordinary_reads<=0;tile_proven<=0;')
    s=s.replace('manifest_at<=0;','')
    a=s.index('PREAD:state<=PCAP;');b=s.index('\n     PUT:if(',a)
    s=s[:a]+'''PREAD:state<=PCAP;
     PCAP:begin held<=qdata;state<=ordinary_mode?OBYTE:PUT;end
'''+s[b:]
    a=s.index('     OSETUP:begin');b=s.index('\n     default:;',a)
    s=s[:a]+'''     OSETUP:begin ordinary_mode<=1;at<=0;state<=OPUSH;end
     OPUSH:if(mready)state<=OMETA;
     OMETA:if(mready)begin
      if(at==7)state<=OREPLY;else begin at<=at+1'b1;state<=OPUSH;end
     end
     OREPLY:if(bv)begin
      if(reply==0)state<=ORET;
      else if(reply<16||{1'b0,reply}>=qlen)failed<=1;
      else begin parser_address<=reply;state<=PREAD;end
     end
     OBYTE:if(mready)state<=OBWAIT;
     OBWAIT:if(mready)state<=OREPLY;
     ORET:begin
      if(header[0]==15)manifest_phase<=1;
      if(header[0]==3)begin at<=0;manifest_phase<=2;end
      ordinary_mode<=0;qretire<=1;packet_seq<=packet_seq+1'b1;state<=BRET;
     end
''' + s[b:]
    return s


CFG_BIND='.cfg_valid272(cfg_valid272),.cfg_ready272(cfg_ready272),.cfg_at272(cfg_at272),.cfg_data272(cfg_data272),.cfg_context272(cfg_context272),'
CFG_CORE='''input wire cfg_valid272,output wire cfg_ready272,input wire [2:0] cfg_at272,
 input wire [15:0] cfg_data272,output wire [119:0] cfg_context272,
'''
CFG_FLOW='''output wire cfg_valid272,input wire cfg_ready272,output wire [2:0] cfg_at272,
 output wire [15:0] cfg_data272,input wire [119:0] cfg_context272,
'''


def share_context(d):
    # Input query/row registers are dead after source commit. Reuse them only
    # in output phase and with no query outstanding. No RAM port is added.
    p=d/'nes_core257.sv';s=p.read_text()
    s=once(s,'module nes_core257(', 'module nes_core257(\n '+CFG_CORE)
    s=once(s,' assign query=raw_query',
        ''' assign cfg_ready272=!reset&&!abort_source&&!fault&&lease_ok&&output_phase&&!q_pending;
 assign cfg_context272={q_raw_seen,q_maps,edge1[1],edge1[0],edge0,new2,new1,old2,old1,q_held};
 assign query=raw_query''')
    s=once(s,'    if(q_want)begin', '''    if(cfg_valid272&&cfg_ready272)case(cfg_at272)
     0:q_held[15:0]<=cfg_data272;
     1:q_held[31:16]<=cfg_data272;
     2:q_held[47:32]<=cfg_data272;
     3:q_held[63:48]<=cfg_data272;
     4:begin edge0<=cfg_data272[7:0];edge1[1:0]<=cfg_data272[9:8];end
     5:begin old1<=cfg_data272[7:0];old2<=cfg_data272[15:8];end
     6:begin new1<=cfg_data272[7:0];new2<=cfg_data272[15:8];end
     7:begin q_maps<=cfg_data272[10:0];q_raw_seen<=cfg_data272[13:11];end
    endcase
    if(q_want)begin''')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text()
    s=once(s,'module nes_joint257(', 'module nes_joint257(\n '+CFG_CORE)
    s=once(s,'nes_core257 encoder(', 'nes_core257 encoder('+CFG_BIND)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' wire display_write,',''' wire cfg_valid272,cfg_ready272;wire [2:0] cfg_at272;
 wire [15:0] cfg_data272;wire [119:0] cfg_context272;
 wire display_write,''')
    s=once(s,' flow(', ' flow('+CFG_BIND)
    s=once(s,'nes_joint257 core(', 'nes_joint257 core('+CFG_BIND)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s=' '+s,a='(\n input wire [48:0] link270',b='(\n '+CFG_FLOW+' input wire [48:0] link270').lstrip()
    s=once(s,'nes_parser272 parser272(', 'nes_parser272 parser272('+CFG_BIND)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_parser272.sv';s=p.read_text()
    s=once(s,'module nes_parser272(', 'module nes_parser272(\n '+CFG_FLOW)
    s=once(s,' reg [7:0] header[0:15],parser_address,at;', ''' wire [7:0] header[0:15];reg [7:0] parser_address,at;
 assign {header[15],header[14],header[13],header[12],header[11],header[10],header[1],header[0]}=cfg_context272[63:0];''')
    s=once(s,' reg [8:0] qlen,manifest_at;', ' wire [8:0] qlen=cfg_context272[104:96];reg [8:0] manifest_at;')
    s=once(s,' reg [31:0] token;reg tile_proven;reg [10:0] scroll_length;reg [2:0] prelude_raw;', ''' wire [31:0] token=cfg_context272[95:64];wire tile_proven=cfg_context272[105];
 wire [10:0] scroll_length=cfg_context272[116:106];wire [2:0] prelude_raw=cfg_context272[119:117];
 assign cfg_valid272=word_valid&&word_ready&&state==LOAD&&!word_byte;
 assign cfg_at272=meta_at;assign cfg_data272=word_data;''')
    s=once(s,'(state==LOAD||state==RECV)', '((state==LOAD&&cfg_ready272)||state==RECV)')
    s=once(s,'qdata<=0;qlen<=0;token<=0;\n   tile_proven<=0;scroll_length<=0;prelude_raw<=0;', 'qdata<=0;')
    a=s.index('     case(meta_at)');b=s.index('     meta_at<=',a);s=s[:a]+s[b:]
    s=once(s,'LOAD:if(word_valid)', 'LOAD:if(word_valid&&word_ready)')
    p.write_text(s,encoding='utf-8',newline='\n')


def patch(d,src=None,pins=None,shared=False):
    p=d/'nes_mux260.sv';s=p.read_text(encoding='utf-8')
    (d/'nes_parser272.sv').write_text(parser(s),encoding='utf-8',newline='\n')
    p.write_text(flow(s),encoding='utf-8',newline='\n')
    if shared:share_context(d)
    if src is not None:src['nes_parser272.sv']=''
    if pins is not None:pins['nes_joint272.py']=sha(ROOT/'tools/nes_joint272.py')
