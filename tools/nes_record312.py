# SPDX-License-Identifier: MIT
"""Canonical admission record and one RAM reader; legacy consumer view retained.

This removes the host header reader, but deliberately does not claim removal
of the ordinary SNES adapter or validator packet decoder yet.
Encoded length still has the legacy wire-plen meaning; receipt bounds and
codec normalization remain in the retained execution logic. Reserved record
bytes must not be mistaken for implemented NES311 certificate fields.
"""
from nes_delta231 import once


def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'input wire parser_retire,', '''input wire frame_start312,input wire [31:0] frame_serial312,
 input wire [15:0] frame_generation312,output reg [191:0] record312,
 input wire parser_retire,''')
    s=once(s,'reg [15:0] accepted,retired,consumed312;','')
    s=once(s,'reg [8:0] lengths[0:1];','''reg [15:0] accepted,retired,consumed312;
 reg [15:0] sequence312,ingress_length312;
 reg [7:0] opcode312;
 reg bad_header312,loaded312,loading312;
 reg [4:0] load_at312,clear_at312;
 reg clearing312,mirror312;
 reg [4:0] mirror_at312;reg [7:0] mirror_data312;
 wire [9:0] write_base312=accepted[0]?10'd752:10'd480;
 wire [9:0] read_base312=retired[0]?10'd752:10'd480;
 wire [7:0] head_op312=record312[7:0];
 wire [4:0] prefix312=head_op312==14?5'd21:head_op312==12?5'd20:5'd16;
 wire [4:0] write_prefix312=opcode312==14?5'd21:opcode312==12?5'd20:5'd16;
 wire [15:0] encoded312=record312[79:64];
 function automatic [4:0] field312(input [7:0] i);
  case(i)
   0,1,2,3:field312=i[4:0];
   10,11:field312=i-6;
   12,13:field312=i-4;
   14,15:field312=i-8;
   default:field312=0;
  endcase
 endfunction
 function automatic [7:0] identity312(input [3:0] i);
  case(i)
   2:identity312=sequence312[7:0];3:identity312=sequence312[15:8];
   4:identity312=frame_serial312[7:0];5:identity312=frame_serial312[15:8];
   6:identity312=frame_serial312[23:16];7:identity312=frame_serial312[31:24];
   8:identity312=frame_generation312[7:0];9:identity312=frame_generation312[15:8];
   default:identity312=0;
  endcase
 endfunction''')
    a=s.index(' always @(posedge clk)read_data<=');b=s.index(' wire [7:0] common_crc270',a)
    s=s[:a]+''' wire [9:0] read_address312=read_base312+(loading312?{5'd0,load_at312}:10'd24+{2'd0,sn_address}-{5'd0,prefix312});
 always @(posedge clk)read_data<=buffer[read_address312];
 reg [7:0] virtual312;
 always @*begin
  virtual312=read_data;
  if(sn_address<16)begin
   if(sn_address>=4&&sn_address<=9)begin
    case(sn_address)
     4:virtual312=frame_serial312[7:0];5:virtual312=frame_serial312[15:8];
     6:virtual312=frame_serial312[23:16];7:virtual312=frame_serial312[31:24];
     8:virtual312=frame_generation312[7:0];default:virtual312=frame_generation312[15:8];
    endcase
   end else virtual312=record312[field312(sn_address)*8+:8];
  end else if(sn_address<prefix312)virtual312=record312[(sn_address-6)*8+:8];
 end
 assign sn_data=virtual312;
 assign packet_ready=used!=0&&loaded312&&enable&&!reset&&!fault;
 assign packet_length=packet_ready?encoded312[8:0]+9'd16:9'd0;
'''+s[b:]
    s=once(s,'can_write<=0;', '''can_write<=0;sequence312<=0;opcode312<=0;bad_header312<=0;
   loaded312<=0;loading312<=0;load_at312<=0;record312<=0;ingress_length312<=0;
   clearing312<=0;clear_at312<=0;mirror312<=0;mirror_at312<=0;mirror_data312<=0;''')
    s=once(s,'if(consume_record312&&enable&&!fault)', '''if(frame_start312)sequence312<=0;
   if(!fault&&enable)begin
    if(!loaded312&&!loading312&&used!=0)begin loading312<=1;load_at312<=0;end
    else if(loading312)begin
     if(load_at312!=0)record312[(load_at312-1)*8+:8]<=read_data;
     if(load_at312==24)begin loading312<=0;loaded312<=1;end
     else load_at312<=load_at312+1'b1;
    end
    if(clearing312)begin
     buffer[write_base312+{5'd0,clear_at312}]<=clear_at312==16?8'd24:8'd0;
     if(clear_at312==23)clearing312<=0;else clear_at312<=clear_at312+1'b1;
    end else if(mirror312)begin buffer[write_base312+{5'd0,mirror_at312}]<=mirror_data312;mirror312<=0;end
   end
   if(consume_record312&&enable&&!fault)''')
    s=once(s,"else retired<=retired+1'b1;", "else begin retired<=retired+1'b1;loaded312<=0;loading312<=0;end")
    s=once(s,'!can_write||!enable||fault||!link270[108]', "!can_write||!enable||fault||bad_header312||clearing312||mirror312||sequence312==65535||ingress_length312!={7'd0,byte_count}-16'd19||!link270[108]")
    s=once(s,"else begin lengths[accepted[0]]<=byte_count-9'd3;accepted<=accepted+1'b1;end", "else begin accepted<=accepted+1'b1;sequence312<=sequence312+1'b1;end")
    s=once(s,'can_write<=enable&&!full&&!fault;', '''can_write<=enable&&!full&&!fault;
      bad_header312<=0;
      if(incoming==8'he1&&enable&&!full&&!fault)begin clearing312<=1;clear_at312<=0;end''')
    s=once(s,"if(can_write&&byte_count<=256)buffer[(accepted[0]?10'd752:10'd480)+byte_count-1'b1]<=incoming;", '''if(can_write&&!fault&&byte_count<=256)begin
       if(clearing312||mirror312)fault<=1;
       else if(byte_count<=16)begin
        if(byte_count>=3&&byte_count<=10&&incoming!=identity312(byte_count-1))bad_header312<=1;
        if(byte_count==1)opcode312<=incoming;
        if(byte_count==13)ingress_length312[7:0]<=incoming;
        if(byte_count==14)ingress_length312[15:8]<=incoming;
        if(byte_count<=4||byte_count>=11)buffer[write_base312+{5'd0,field312(byte_count-1)}]<=incoming;
       end else if(byte_count<={4'd0,write_prefix312})begin
        buffer[write_base312+byte_count-7]<=incoming;
       end else buffer[write_base312+10'd24+byte_count-1'b1-{5'd0,write_prefix312}]<=incoming;
      end''')
    # An explicit single port is required: independent procedural assignments
    # make Quartus infer multiple write ports and turn this RAM into registers.
    s=once(s,"buffer[write_base312+{5'd0,clear_at312}]<=clear_at312==16?8'd24:8'd0;",'')
    s=once(s,"buffer[write_base312+{5'd0,mirror_at312}]<=mirror_data312;",'')
    s=once(s,'if(byte_count<=4||byte_count>=11)buffer[write_base312+{5\'d0,field312(byte_count-1)}]<=incoming;', '')
    s=once(s,"buffer[write_base312+byte_count-7]<=incoming;",'')
    s=once(s,"else buffer[write_base312+10'd24+byte_count-1'b1-{5'd0,write_prefix312}]<=incoming;",'else begin end')
    s=once(s,'wire ours=', '''reg write312;reg [9:0] write_address312;reg [7:0] write_data312;
 always @*begin
  write312=0;write_address312=0;write_data312=0;
  if(!reset&&!fault&&enable)begin
   if(clearing312)begin
    write312=1;write_address312=write_base312+{5'd0,clear_at312};write_data312=clear_at312==16?8'd24:8'd0;
   end else if(!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&command==8'he1&&can_write&&byte_count!=0&&byte_count<=256)begin
    write_data312=incoming;
    if(byte_count<=16)begin
     if(byte_count<=4||byte_count>=11)begin write312=1;write_address312=write_base312+{5'd0,field312(byte_count-1)};end
    end else begin
     write312=1;
     if(byte_count<={4'd0,write_prefix312})write_address312=write_base312+byte_count-7;
     else write_address312=write_base312+10'd24+byte_count-1'b1-{5'd0,write_prefix312};
    end
   end
  end
 end
 always @(posedge clk)if(write312)buffer[write_address312]<=write_data312;
 wire ours=''')
    # Load the single host active record directly. Keeping a second 192-bit
    # snapshot in the queue defeats the replacement boundary.
    s=once(s,'output reg [191:0] record312,', '''input wire [191:0] record312,input wire load_enable312,
 output wire record_valid312,output wire [4:0] record_at312,output wire [7:0] record_byte312,''')
    s=once(s,';record312<=0;', ';')
    s=once(s,'!loaded312&&!loading312&&used!=0','!loaded312&&!loading312&&used!=0&&load_enable312')
    s=once(s,"if(load_at312!=0)record312[(load_at312-1)*8+:8]<=read_data;", '')
    s=once(s,'assign sn_data=virtual312;', '''assign record_valid312=loading312&&load_at312!=0&&!reset&&!fault;
 assign record_at312=load_at312-1'b1;assign record_byte312=read_data;
 assign sn_data=virtual312;''')
    s=once(s,'input wire load_enable312,', 'input wire load_enable312,output wire storage_empty312,')
    s=once(s,'assign packet_ready=', "assign storage_empty312=used==0;\n assign packet_ready=")
    # Ingress checks identity and actual wire length before publication.
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'wire [127:0] progress_status;', '''wire [127:0] progress_status;
 wire [191:0] record312={72'd0,active305.left,active305.token,active305.encoded,active305.span,active305.start,packet_seq,active305.section,active305.op};
 wire record_valid312,storage_empty312;wire [4:0] record_at312;wire [7:0] record_byte312;''')
    s=once(s,'nes_queue260 queue(', '''nes_queue260 queue(.frame_start312(grant278),.frame_serial312(identity[31:0]),
 .frame_generation312(identity[47:32]),.record312(record312),.load_enable312(state==IDLE&&!qretire),
 .storage_empty312(storage_empty312),.record_valid312(record_valid312),.record_at312(record_at312),.record_byte312(record_byte312),''')
    s=once(s,'state!=IDLE||owner!=NONE||qr||trequest', 'state!=IDLE||owner!=NONE||!storage_empty312||trequest')
    a=s.index('else if(qr&&have_identity&&!qretire)begin');b=s.index('     CHECK:begin',a)
    s=s[:a]+'''else if(qr&&have_identity&&!qretire)begin
       qlen<=queue_length312;at<=0;
       state<=CHECK;
      end
'''+s[b:]
    # Keep symbol values as reserved holes so old observer IDs do not shift;
    # remove the actual host header read/capture execution states.
    s=s.replace('HREAD=1,HCAP=2,','')
    s=once(s,'if(pe||ce||tfault||qfault)failed<=1;', '''if(pe||ce||tfault||qfault)failed<=1;
   if(record_valid312&&!fault)begin
    if(state!=IDLE)failed<=1;
    else case(record_at312)
     0:active305.op<=record_byte312;1:active305.section<=record_byte312;
     2:if(record_byte312!=packet_seq[7:0])failed<=1;
     3:if(record_byte312!=packet_seq[15:8])failed<=1;
     4:active305.start[7:0]<=record_byte312;5:active305.start[15:8]<=record_byte312;
     6:active305.span[7:0]<=record_byte312;7:active305.span[15:8]<=record_byte312;
     8:active305.encoded[7:0]<=record_byte312;9:active305.encoded[15:8]<=record_byte312;
     10:active305.token[7:0]<=record_byte312;11:active305.token[15:8]<=record_byte312;
     12:active305.token[23:16]<=record_byte312;13:active305.token[31:24]<=record_byte312;
     14:active305.left<=record_byte312;
     default:;
    endcase
   end''')
    p.write_text(s,newline='\n')
