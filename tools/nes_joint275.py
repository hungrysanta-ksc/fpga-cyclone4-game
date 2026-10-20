# SPDX-License-Identifier: MIT
"""Replace host ordinary interpretation with descriptor-bound inline references.

Source/query and the shared core remain charged. No added parser module,
packet RAM or mailbox. This is a measured replacement candidate, not a claim
that the entire source/core/queue has become one FSM.
"""
from nes_delta231 import ROOT,once

def flow(s):
 s=once(s,' reg [5:0] state;', ''' localparam RNEXT=40,RREAD=41,RCAP=42,RDECODE=43,RDATA=44,RADVANCE=45,RTAGREAD=46,RTAGCAP=47,RLENREAD=48,RLENCAP=49;
 reg inline275;reg [8:0] logical_length275;
 wire [8:0] wire_length275;
 reg [5:0] state;''')
 s=once(s,'wire [8:0] qlen;', 'wire [8:0] qlen=inline275?logical_length275:wire_length275;')
 s=once(s,'.packet_length(qlen)', '.packet_length(wire_length275)')
 s=once(s,'wire [7:0] qaddr=state==NORMAL?asyn[7:0]:parser_address;',
 '''wire physical275=state==RREAD||state==RCAP||state==RLENREAD||state==RLENCAP;
 wire [7:0] qaddr=(state==NORMAL?asyn[7:0]:parser_address)+
  (inline275&&!physical275?8'd2:8'd0);''')
 s=once(s,'state<=IDLE;owner<=NONE;', 'inline275<=0;logical_length275<=0;state<=IDLE;owner<=NONE;')
 s=once(s,'else if(qr&&have_identity)begin parser_address<=0;', 'else if(qr&&have_identity)begin inline275<=0;parser_address<=0;')
 s=once(s,'     HCAP:begin\n', '''     RLENREAD:state<=RLENCAP;
     RLENCAP:begin
      if(qdata<15||{1'b0,qdata}+9'd3>=wire_length275)failed<=1;
      else begin logical_length275<={1'b0,qdata}+1'b1;inline275<=1;at<=0;parser_address<=0;state<=HREAD;end
     end
     HCAP:if(at==0&&qdata==0&&!inline275)begin parser_address<=1;state<=RLENREAD;end else begin
''')
 s=once(s,'if(header[0]==0||header[0]>15||',
 '''if((inline275&&(header[0]==1||header[0]==12||header[0]==13||header[0]==14))||header[0]==0||header[0]>15||''')
 # Keep the token read for already-consumed tile DMA; all other PCAP reads
 # are references to the same immutable logical packet shown to SNES.
 a=s.index('      end else if(header[0]==15)begin',s.index('PREAD:state<=PCAP'))
 b=s.index('\n     PUT:if(',a)
 s=s[:a]+'''      end else begin
       opos<=opos+1'b1;rle_left<=rle_left-1'b1;
       if(header[20]==9)event264(5,{10'd0,qdata},3'd1);
       else begin
        if(header[0]!=15)manifest_at<=manifest_at+1'b1;
        event264(header[20]==11?4'd7:4'd3,{10'd0,qdata},3'd1);
       end
      end
     end
'''+s[b:]
 s=once(s,'ordinary_mode<=1;opos<=startpos[11:0];oend<=startpos[11:0]+outlen[11:0];',
 '''ordinary_mode<=1;opos<=startpos[11:0];oend<=startpos[11:0]+outlen[11:0];
      cursor<=inline275?qlen+9'd2:wire_length275;rle_left<=0;rle_zero<=0;''')
 s=once(s,'manifest_phase<=1;opos<=16;oend<=206;state<=OREAD;parser_address<=16;',
            'manifest_phase<=1;opos<=16;oend<=206;state<=RNEXT;')
 s=once(s,'opos<=16;oend<=qlen;parser_address<=16;rle_left<=0;state<=OREAD;',
            'opos<=16;oend<=qlen;state<=RNEXT;')
 s=once(s,"manifest_phase<=2;event264(4,18'd3,3'd5);",
            'opos<=0;oend<=3;state<=RNEXT;')
 s=once(s,'else state<=OSELECT;', 'else begin if(header[1]==4)opos<=startpos[11:0]+outlen[11:0];state<=RNEXT;end')
 a=s.index('     OTILE:if(');b=s.index('     ORET:begin',a)
 s=s[:a]+'''     OTILE:state<=RNEXT;
'''+(ROOT/'tools/nes_inline275.sv.inc').read_text()+'''
     OISSUE:if(mready)state<=OWAIT;
     OWAIT:if(mready)state<=event_return==0?RNEXT:RADVANCE;
'''+s[b:]
 return s

def patch(d):
 p=d/'nes_mux260.sv';p.write_text(flow(p.read_text()),encoding='utf-8',newline='\n')
 p=d/'nes_queue260.sv';s=p.read_text()
 # Transaction length is authoritative; the flow checks the logical header.
 # CRC-CCITT big-endian trailer has zero residue. This removes the duplicate
 # payload-length and received-CRC registers instead of adding a prefix parser.
 s=once(s,'payload_size,request_crc,received_crc','request_crc')
 s=once(s," wire [16:0] expected_length={1'b0,payload_size}+17'd16;",'')
 s=s.replace('payload_size<=0;','').replace('received_crc<=0;','')
 s=once(s,'payload_size>240||byte_count!=expected_length+3||bit_count!=0||received_crc!=request_crc',
        'byte_count<19||byte_count>259||bit_count!=0||request_crc!=0')
 s=once(s,'expected_length[8:0]',"byte_count-9'd3")
 a=s.index('      if(byte_count==13)payload_size');b=s.index('\n     end',a)
 s=s[:a]+'''      request_crc<=crc16(request_crc,incoming);
      if(can_write&&byte_count<=256)buffer[{accepted[1:0],8'd0}+byte_count-1'b1]<=incoming;
'''+s[b:]
 p.write_text(s,encoding='utf-8',newline='\n')
