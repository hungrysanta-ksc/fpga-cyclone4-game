# SPDX-License-Identifier: MIT
"""Direct host receipt/manifest progression and shared in-transfer status.

Keep the compact wire, independent validator predicates, physical read/ACK,
fixed RAM ownership and concurrent immutable plan banks. No trusted ARM hints.
"""
import re
from nes_delta231 import once
from nes_joint280 import patch as prior_patch


def flow(s):
    s=once(s,'input wire init278,','input wire init278,\n input wire [8:0] manifest_at282,input wire manifest_started282,')
    s=s.replace('wire mv,mready;wire [23:0] md;','wire mready;')
    s=s.replace(' reg [23:0] consumer_word;','')
    s=s.replace('reg [8:0] manifest_at,ordinary_reads;', 'reg [8:0] ordinary_reads;wire [8:0] manifest_at=manifest_at282;')
    s=s.replace('reg [1:0] manifest_phase;', "wire [1:0] manifest_phase=!begun?2'd0:sealed?2'd2:manifest_started282?2'd1:2'd0;")
    s=s.replace(' reg [2:0] event_return;','')
    a=s.index(' task event264(');b=s.index(' reg bad_data278;',a);s=s[:a]+s[b:]
    a=s.index(' wire consumer_event=');b=s.index(' (* altera_attribute=',a)
    s=s[:a]+''' // One descriptor is held until validator acceptance; no encoded event/return.
 reg [11:0] receipt_first282,receipt_count282,receipt_end282;
 reg receipt_valid282;
 always @*begin
  receipt_first282=0;receipt_count282=0;receipt_end282=opos;receipt_valid282=0;
  if(state==OTILE&&opos<oend)begin
   receipt_first282=opos;receipt_count282=oend-opos>16?12'd16:oend-opos;
   receipt_end282=opos+receipt_count282;receipt_valid282=1;
  end else if(state==OSELECT&&opos<oend)begin
   if(header[1]==3)begin
    receipt_first282=1152+(opos>>4);receipt_end282=oend-opos>256?opos+12'd256:oend;
    receipt_count282=(receipt_end282-opos)>>4;receipt_valid282=1;
   end else if(header[1]==5&&opos>=1121&&opos<3169)begin
    receipt_end282=oend<3169?oend:12'd3169;
    if(receipt_end282-opos>256)receipt_end282=opos+12'd256;
    receipt_first282=1184+(boff>>4);receipt_count282=(receipt_end282-opos)>>4;receipt_valid282=1;
   end else if(header[1]==5&&opos>=3169&&prelude_raw!=0)begin
    receipt_first282=1312+{8'd0,hoff[7:4]};receipt_count282=1;
    receipt_end282=opos+(hoff[7:4]==15?12'd9:12'd16);
    receipt_valid282=tap_crc_mask278[hoff[7:4]];
   end
  end
 end
 wire manifest_byte282=ordinary_mode&&state==PCAP&&
  (header[0]==15||header[0]==10||(header[0]==11&&opos!=16&&rle_left!=0));
 wire zero_byte282=state==ORLE&&rle_left!=0&&rle_zero;
 assign display_write=manifest_byte282&&header[0]==15&&opos<40&&range_ready&&!rst;
 assign display_request=state==DREQ&&display_request_ready&&!rst;
 assign ordinary_range=receipt_valid282&&range_ready&&!rst;
 assign ordinary_first=receipt_first282;assign ordinary_count=receipt_count282;
 assign ordinary_byte=tap_byte278?tap_value278:zero_byte282?8'd0:qdata;
 assign ordinary_stream=1'b0;
 assign ordinary_check=(zero_byte282||(manifest_byte282&&!(header[0]==15&&opos<40)))&&range_ready&&!rst;
 assign ordinary_hash_start=(tap_start278||state==OCERT||state==OISSUE)&&range_ready&&!rst;
 assign ordinary_hash_kind=tap_start278?(tap_raw278?2'd0:2'd1):state==OISSUE?2'd3:2'd2;
 assign ordinary_hash_index=tap_relative278[7:4];
 assign ordinary_hash_byte=tap_byte278&&!rst;
 assign ordinary_finish=state==OFINISH&&range_ready&&!rst;
 assign mready=state==DREQ?display_request_ready:prelude_mode?context_ready:range_ready;
 assign context_valid=prelude_mode&&state==PUT&&!rst;assign context_data=held;
 assign begin_valid=state==BSTART&&range_ready&&!rst;
 assign begin_bank=identity[48];assign begin_raw=prelude_raw;
 assign range_first=first;assign range_count=count;assign range_valid=state==SEND&&range_ready&&!rst;
 assign range_dma_done=0;
 wire bv=state==DWAIT?display_response_valid:range_ready;
 wire [7:0] reply=display_response;
 assign display_response_ready=state==DWAIT&&!rst;
'''+s[b:]
    for old in ['consumer_word<=0;','event_return<=0;','manifest_at<=0;','manifest_phase<=0;','manifest_phase<=1;','manifest_phase<=2;','manifest_at<=manifest_at+1\'b1;']:
        s=s.replace(old,'')
    s=s.replace('end else begin\n      held<=qdata;', 'end else if(range_ready)begin\n      held<=qdata;')
    # Keep validator acceptance and host cursor movement on the SAME edge.
    s=once(s,"       if(opos<40)event264(7,{10'd0,qdata},3'd3);\n       else event264(3,{10'd0,qdata},3'd3);",'       state<=OCHECKNEXT;')
    s=s.replace("event264(3,{10'd0,qdata},3'd3);",'state<=OCHECKNEXT;')
    s=s.replace("event264(3,{10'd0,qdata},3'd4);",'state<=ORLE;')
    s=s.replace("end else begin opos<=opos+1'b1;event264(5,{10'd0,qdata},3'd1);end",'end else failed<=1;')
    s=s.replace("event264(4,18'd3,3'd5);",'state<=OISSUE;')
    a=s.index('     OTILE:');b=s.index('     ORLE:',a)
    s=s[:a]+'''     OTILE:if(range_ready)begin
      if(opos==oend)state<=ORET;else opos<=receipt_end282;
     end
     OSELECT:if(range_ready)begin
      if(opos==oend||header[1]==4)state<=ORET;
      else if(header[1]==3)begin
       if(opos[3:0]!=0||oend[3:0]!=0)failed<=1;else opos<=receipt_end282;
      end else if(opos<scroll_length)opos<=scroll_length;
      else if(opos<1121)opos<=oend<1121?oend:12'd1121;
      else if(opos<3169)begin
       if(boff[3:0]!=0||(oend<3169&&(oend-12'd1121)%16!=0))failed<=1;
       else opos<=receipt_end282;
      end else if(prelude_raw==0)state<=ORET;
      else if(!tap_crc_mask278[hoff[7:4]])failed<=1;
      else opos<=receipt_end282;
     end
'''+s[b:]
    s=s.replace('     ORLE:begin','     ORLE:if(range_ready)begin')
    s=s.replace("event264(3,18'd0,3'd4);",'')
    a=s.index('     OISSUE:');b=s.index('     ORET:',a)
    s=s[:a]+'''     OISSUE:if(range_ready)state<=OCERT;
     OCERT:if(range_ready)state<=OFINISH;
     OFINISH:if(range_ready)state<=ORET;
'''+s[b:]
    assert 'event264' not in s and 'event_return' not in s and 'consumer_word' not in s
    # qretire is owned by this FSM. Eliminate the extra BRET return bubble.
    s=s.replace('state<=BRET;', 'state<=IDLE;')
    s=once(s,'else if(qr&&have_identity)begin','else if(qr&&have_identity&&!qretire)begin')
    return s


def apply(d):
    # One status-bit driver serves queue and plan replies. Source payload SPI
    # retains its own data path; STOP still gates each endpoint selection.
    for p in d.glob('*.sv'):
        s=p.read_text().replace('[106:0] link270','[107:0] link270').replace('[106:0] link);','[107:0] link);')
        p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_mux260.sv';p.write_text(flow(p.read_text()),encoding='utf-8',newline='\n')
    # The validator's checked cursor is the sole manifest progress counter.
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'module nes_validator278(', 'module nes_validator278(output wire [8:0] manifest_at282,output wire manifest_started282,')
    s=once(s,' assign ram_addr=', " assign manifest_at282=cursor>=166?cursor-10'd166:9'd0;\n assign manifest_started282=rec_i!=0||cursor!=0;\n assign ram_addr=")
    p.write_text(s,encoding='utf-8',newline='\n')
    for name in ('nes_joint257.sv','nes_joint266.sv'):
        p=d/name;s=p.read_text()
        if name=='nes_joint257.sv':
            s=once(s,'module nes_joint257(', 'module nes_joint257(output wire [8:0] manifest_at282,output wire manifest_started282,')
            s=once(s,'nes_validator278 validator(', 'nes_validator278 validator(.manifest_at282(manifest_at282),.manifest_started282(manifest_started282),')
        else:
            s=once(s,'wire [2:0] source_raw278;', 'wire [8:0] manifest_at282;wire manifest_started282;\nwire [2:0] source_raw278;')
            for mark in (' flow(', 'nes_joint257 core('):s=once(s,mark,mark+'.manifest_at282(manifest_at282),.manifest_started282(manifest_started282),')
        p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,' assign link[48:0]=', ''' reg reply_bit282;
 assign link[107]=reply_bit282;
 always @(posedge clk or posedge reset)begin
  if(reset)reply_bit282<=0;
  else if(ss[1])reply_bit282<=0;
  else if(!sck[1]&&prev_sck)reply_bit282<=reply[7-bits];
 end
 assign link[48:0]=''')
    s=once(s,"       8'he8:begin", """       8'he1,8'he9:begin
        snapshot<={8'hfa,output_status[175:128],plan_status[167:144],104'd0};status_length<=11;
       end
       8'he8:begin""")
    p.write_text(s,encoding='utf-8',newline='\n')
    for name in ('nes_queue260.sv','nes_plan_spi200.sv'):
        p=d/name;s=p.read_text()
        s=s.replace('reg miso_hold,','reg ').replace('miso_hold<=0;','')
        s=s.replace('assign miso=miso_hold;', 'assign miso=link270[107];')
        s=re.sub(r'   if\(!ss\[1\]&&!sck\[1\]&&prev_sck\)miso_hold<=reply\[7-(?:bit_count|bits)\];','',s)
        s=s.replace('reg [7:0] reply;','')
        s=s.replace(' always @*begin\n  reply=status_reply270;\n end','')
        assert 'miso_hold' not in s
        p.write_text(s,encoding='utf-8',newline='\n')


def patch(d):
    prior_patch(d);apply(d)
