# SPDX-License-Identifier: MIT
"""Post-ACK queue reader: direct receipt/hash/manifest, no SNES byte echo.

Candidate scope: immutable packet aperture read plus checked ACK attests ordinary
execution; actual PPU writes still need the target consumer. Tile receipt also
requires the existing sequential DMA read/token consume proof.
"""
from nes_joint263 import sources as prior
from nes_delta231 import once

DECL = '''
 reg ordinary_mode;reg [11:0] opos,oend;reg [10:0] scroll_length;
 reg [8:0] manifest_at,ordinary_reads;
 reg [1:0] manifest_phase;
 reg [7:0] rle_left;reg rle_zero,tile_proven;
 reg [5:0] after_event;
 wire [11:0] hoff=opos-12'd3169;
 wire [11:0] boff=opos-12'd1121;
 wire [15:0] plen={header[13],header[12]};
 wire [15:0] startpos={header[11],header[10]};
 wire [15:0] outlen=header[0]==2?plen:{header[15],header[14]};
 task event264(input [3:0] k,input [17:0] value,input [5:0] continuation);
 begin consumer_word<={2'b10,k,value};after_event<=continuation;state<=OISSUE;end
 endtask
'''

STATES = '''
     OSETUP:begin
      ordinary_mode<=1;opos<=startpos[11:0];oend<=startpos[11:0]+outlen[11:0];
      if(header[0]==7)begin
       if(!tile_proven||header[1]>1||plen!=4||!outlen||outlen>2048||
          (header[1]==0?(startpos[3:0]!=0||outlen[3:0]!=0||startpos+outlen>16384):
                       (startpos[4:0]!=0||outlen[4:0]!=0||startpos+outlen>4096)))failed<=1;
       else begin opos<=(header[1]==1?12'd1024:0)+(startpos>>(header[1]==1?5:4));
        oend<=(header[1]==1?12'd1024:0)+((startpos+outlen)>>(header[1]==1?5:4));parser_address<=16;at<=0;state<=OTREAD;end
      end else if(header[0]==15)begin
       if(manifest_phase!=0||qlen!=206||header[1]!=0||plen!=190||startpos!=0||outlen!=0)failed<=1;
       else begin manifest_phase<=1;opos<=40;oend<=206;state<=OREAD;parser_address<=40;end
      end else if(header[0]==10||header[0]==11)begin
       if(manifest_phase!=1||header[1]!=2||startpos!=manifest_at||outlen!=0||plen==0)failed<=1;
       else begin opos<=16;oend<=qlen;parser_address<=16;rle_left<=0;state<=OREAD;end
      end else if(header[0]==3)begin
       if(manifest_phase!=1||manifest_at!=256||qlen!=16||plen!=0||startpos!=0||outlen!=0||header[1]!=0)failed<=1;
       else begin manifest_phase<=2;event264(4,18'd3,OCERT);end
      end else if(header[0]==2||header[0]==4||header[0]==5||header[0]==8)begin
       if(manifest_phase!=0||!outlen||startpos+outlen>(header[1]==3?512:header[1]==4?544:header[1]==5?3418:0)||
          (header[0]==2?outlen!=plen:header[0]==8?(plen!=4||outlen[1:0]!=0):(plen!=2||outlen[0]!=0)))failed<=1;
       else if(header[1]==5&&((startpos<scroll_length&&(startpos!=0||startpos+outlen<scroll_length))||
        (startpos+outlen>3169&&((startpos>3169&&(startpos-16'd3169)%16!=0)||
          (startpos+outlen!=3418&&(startpos+outlen-16'd3169)%16!=0)))))failed<=1;
       else state<=OSELECT;
      end else failed<=1;
     end
     OTREAD:state<=OTCAP;
     OTCAP:begin
      if(qdata!=token[at*8+:8])failed<=1;
      else if(at==3)state<=OTILE;
      else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=OTREAD;end
     end
     OTILE:if(opos==oend)state<=ORET;
      else begin opos<=opos+1'b1;event264(1,{6'd1,opos},OTILE);end
     OSELECT:begin
      if(opos==oend)state<=ORET;
      else if(header[1]==4)state<=ORET; // OAM writes have no receipt bits.
      else if(header[1]==3)begin
       if(opos[3:0]!=0||oend[3:0]!=0)failed<=1;
       else begin opos<=opos+16;event264(1,{6'd1,(12'd1152+{4'd0,opos[11:4]})},OSELECT);end
      end else if(opos<scroll_length)begin
       if(opos==0)event264(4,18'd1,ODATA);else state<=ODATA;
      end else if(opos<1121)begin opos<=oend<1121?oend:12'd1121;end
      else if(opos<3169)begin
       if(boff[3:0]!=0||(oend<3169&&(oend-12'd1121)%16!=0))failed<=1;
       else begin opos<=opos+16;event264(1,{6'd1,(12'd1184+{4'd0,boff[11:4]})},OSELECT);end
      end else if(prelude_raw==0)state<=ORET;
      else if(hoff[3:0]==0)event264(4,{12'd0,hoff[7:4],2'd0},ODATA);
      else state<=ODATA;
     end
     ODATA:begin
      parser_address<=16+(header[0]==2?(opos-startpos):header[0]==8?((opos-startpos)&3):((opos-startpos)&1));
      state<=OREAD;
     end
     OREAD:state<=OCAP;
     OCAP:begin
      held<=qdata;
      if(header[0]==15)begin opos<=opos+1'b1;parser_address<=parser_address+1'b1;event264(3,{10'd0,qdata},OCHECKNEXT);end
      else if(header[0]==10)begin
       if(manifest_at>=256)failed<=1;
       else begin manifest_at<=manifest_at+1'b1;opos<=opos+1'b1;parser_address<=parser_address+1'b1;event264(3,{10'd0,qdata},OCHECKNEXT);end
      end else if(header[0]==11)begin
       if(opos==16)begin
        if(qdata!=3||plen<2)failed<=1;
        else begin opos<=opos+1'b1;parser_address<=parser_address+1'b1;state<=OREAD;end
       end else if(rle_left==0)begin
        if(manifest_at+{2'd0,qdata[6:0]}+1>256||(!qdata[7]&&opos+{5'd0,qdata[6:0]}+2>oend))failed<=1;
        else begin rle_left<={1'b0,qdata[6:0]}+1'b1;rle_zero<=qdata[7];opos<=opos+1'b1;parser_address<=parser_address+1'b1;state<=ORLE;end
       end else begin
        rle_left<=rle_left-1'b1;manifest_at<=manifest_at+1'b1;opos<=opos+1'b1;parser_address<=parser_address+1'b1;
        event264(3,{10'd0,qdata},ORLE);
       end
      end else begin opos<=opos+1'b1;event264(5,{10'd0,qdata},OSELECT);end
     end
     ORLE:begin
      if(rle_left!=0&&rle_zero)begin rle_left<=rle_left-1'b1;manifest_at<=manifest_at+1'b1;event264(3,18'd0,ORLE);end
      else if(opos==oend)begin if(rle_left!=0)failed<=1;else state<=ORET;end
      else state<=OREAD;
     end
     OCHECKNEXT:state<=opos==oend?ORET:OREAD;
     OISSUE:if(mready)state<=OWAIT;
     OWAIT:if(mready)state<=after_event;
     OCERT:event264(4,18'd2,OFINISH);
     OFINISH:event264(6,18'd1,ORET);
     ORET:begin ordinary_mode<=0;qretire<=1;packet_seq<=packet_seq+1'b1;state<=BRET;end
'''


def sources():
 src=prior();s=src['nes_queue260.sv']
 # Validation and credit release are separate operations. The head remains
 # immutable and charged to the four-credit window until parser_retire.
 s=once(s,'ack_done<=1;retired<=retired+1\'b1;', 'ack_done<=1;')
 src['nes_queue260.sv']=s
 s=src['nes_mux260.sv']
 s=once(s,'BWAIT=23;', 'BWAIT=23,OSETUP=24,OTILE=25,OSELECT=26,ODATA=27,OREAD=PREAD,OCAP=PCAP,ORLE=30,OCHECKNEXT=31,OISSUE=32,OWAIT=33,OCERT=34,OFINISH=35,ORET=36,OTREAD=PREAD;')
 s=once(s,'reg [4:0] state;', 'reg [5:0] state;')
 s=once(s,' reg [23:0] consumer_word;reg [2:0] consumer_mask;reg consumer_pending;\n wire consumer_idle=!consumer_pending&&mready;',
        ' reg [23:0] consumer_word;\n'+DECL)
 s=s.replace('consumer_pending||state==SEND','state==OISSUE||state==SEND').replace('consumer_pending?consumer_word','state==OISSUE?consumer_word')
 s=once(s,'   consumer_word<=0;consumer_mask<=0;consumer_pending<=0;',
 '''   ordinary_mode<=0;consumer_word<=0;opos<=0;oend<=0;scroll_length<=0;manifest_at<=0;manifest_phase<=0;ordinary_reads<=0;tile_proven<=0;rle_left<=0;rle_zero<=0;after_event<=0;''')
 s=once(s,'   if(consumer_pending&&mready)consumer_pending<=0;','')
 s=once(s,"   8'h64:control=consumer_idle;",'')
 a=s.index("     if(ap>=24'h006060");b=s.index("     if(ap>=24'h006010",a);s=s[:a]+s[b:]
 s=once(s,'if(!ack_publish)failed<=1;', 'if(!ack_publish||ordinary_reads!=qlen||(header[0]==7&&!tile_proven))failed<=1;')
 s=once(s,'header[0]>14','header[0]>15')
 s=once(s,'      else if(header[0]==13)begin', '''      else if(manifest_phase!=0&&header[0]!=10&&header[0]!=11&&header[0]!=3)failed<=1;
      else if(header[0]==13)begin''')
 s=once(s,'      else if(header[0]!=12)state<=NORMAL;', '''      else if(manifest_phase!=0&&header[0]!=10&&header[0]!=11&&header[0]!=3)failed<=1;
      else if(header[0]!=12)begin
       if({header[13],header[12]}+16'd16!={7'd0,qlen})failed<=1;
       else begin ordinary_reads<=0;tile_proven<=0;state<=NORMAL;end
      end''')
 s=once(s,'       else state<=NORMAL;', '       else begin ordinary_reads<=0;tile_proven<=0;state<=NORMAL;end')
 s=once(s,'    if(consume)read_count<=0;', '''    if(tile_consume)begin
     if(state!=NORMAL||header[0]!=7||header[1]!={7'd0,tkind}||
        {header[15],header[14]}!={4'd0,chunk_length}||
        {header[11],header[10]}!=({6'd0,tslot}<<(tkind?5:4)))failed<=1;
     else begin tile_proven<=1;token<=chunk_token;end
    end
    if(state==NORMAL&&rs&&!rp&&ap[23:8]==16'h4000)begin
     if({1'b0,ap[7:0]}!=ordinary_reads||ordinary_reads>=qlen)failed<=1;
     else ordinary_reads<=ordinary_reads+1'b1;
    end
    if(consume)read_count<=0;''')
 s=once(s,'prelude_raw<=held[2:0];', '''prelude_raw<=held[2:0];
      if(prelude_mode&&at==14)scroll_length[7:0]<=held;
      if(prelude_mode&&at==15)scroll_length[10:8]<=held[2:0];''')
 s=once(s,'prelude_done<=0;begun<=0;prelude_mode<=0;tiles_closed<=0;',
        'prelude_done<=0;begun<=0;prelude_mode<=0;tiles_closed<=0;manifest_at<=0;manifest_phase<=0;')
 # The ordinary decoder shares PREAD/PCAP and parser_address with H2/map.
 ordinary_states=STATES
 ta=ordinary_states.index('     OTREAD:');tb=ordinary_states.index('     OTILE:',ta)
 ordinary_states=ordinary_states[:ta]+ordinary_states[tb:]
 ordinary_states=once(ordinary_states,'     OREAD:state<=OCAP;\n','')
 ca=ordinary_states.index('     OCAP:begin');cb=ordinary_states.index('     ORLE:',ca)
 cap=ordinary_states[ca:cb]
 cap=once(cap,'     OCAP:begin', '     PCAP:if(!ordinary_mode)begin held<=qdata;state<=PUT;end else begin')
 cap=once(cap,'      if(header[0]==15)begin', \
 """      if(header[0]==7)begin
       if(qdata!=token[at*8+:8])failed<=1;
       else if(at==3)state<=OTILE;
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else if(header[0]==15)begin""")
 ordinary_states=ordinary_states[:ca]+ordinary_states[cb:]
 s=once(s,'PCAP:begin held<=qdata;state<=PUT;end',cap.strip())
 s=once(s,'assign ordinary_stream=consumer_event&&consumer_kind==2&&!rst;', "assign ordinary_stream=1'b0;")
 s=once(s,"ACKWAIT:if(qdone)begin packet_seq<=packet_seq+1'b1;state<=header[0]==1?BSTART:IDLE;end", '''ACKWAIT:if(qdone)begin
      if(header[0]==1)begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=BSTART;end
      else state<=OSETUP;
     end
'''+ordinary_states)
 src['nes_mux260.sv']=s
 s=src.pop('nes_joint263.sv').replace('nes_joint263','nes_joint264')
 s=once(s,' wire rv,rdone;', ''' reg ordinary_done;
 always @(posedge clk or posedge reset)begin
  if(reset)ordinary_done<=0;else ordinary_done<=v_range_valid&&v_ready&&!abort_source&&!flow_fault&&!lease_fault;
 end
 wire rv,rdone;''')
 s=once(s,'.range_external(rv),',".range_external(1'b1),")
 s=once(s,".range_external(1'b1),\n.range_dma_done(rdone),",".range_external(1'b1),\n.range_dma_done(rdone||ordinary_done),")
 src['nes_joint264.sv']=s
 s=src['nes_core257.sv']
 s=once(s,'reg certificate_ok,digest_ready;', 'reg certificate_ok,digest_ready,scroll_seen;')
 s=s.replace('certificate_ok<=0;digest_ready<=0;', 'certificate_ok<=0;digest_ready<=0;scroll_seen<=0;')
 s=once(s,'h_kind==1&&cursor==422', 'h_kind==1&&cursor==0&&!scroll_seen')
 s=once(s,'      end else if(h_kind==2&&digest_ready&&!certificate_ok)', '''      end else if(h_kind==3&&cursor==422&&scroll_seen&&!digest_ready)begin
       checksum<=digest;h_count<=0;
       if(v_raw)state<=H_HASHREAD;else digest_ready<=1;
      end else if(h_kind==2&&digest_ready&&!certificate_ok)''')
 s=once(s,"      if(v_raw)state<=H_HASHREAD;else begin digest<=crc_result;digest_ready<=1;state<=V_ACTIVE;end", "      digest<=crc_result;scroll_seen<=1;state<=V_ACTIVE;")
 src['nes_core257.sv']=s
 return src
