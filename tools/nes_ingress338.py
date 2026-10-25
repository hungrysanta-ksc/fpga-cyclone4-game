# SPDX-License-Identifier: MIT
"""Aligned immutable packet slots and lifetime-owned D4 descriptors."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'// Four immutable packets;', '// Two immutable 256-byte packets;')
    s=once(s,' reg [7:0] opcode312;\n','')
    a=s.index(' wire [9:0] write_base312=');b=s.index(' function automatic [7:0] identity312',a)
    s=s[:a]+''' // Expected RAM owns 0..471; packet slots own 512..767/768..1023.
 // Preserve the wire packet. Only the active-record loader reorders fields.
 wire [15:0] encoded312=record312[79:64];
 function automatic [7:0] field338(input [3:0] i);
  case(i)
   0,1,2,3:field338={4'd0,i};
   4:field338=10;5:field338=11;
   6:field338=14;7:field338=15;
   8:field338=12;9:field338=13;
   10:field338=16;11:field338=17;12:field338=18;
   13:field338=19;14:field338=20;
   default:field338=0;
  endcase
 endfunction
'''+s[b:]
    s=once(s,"wire [9:0] read_address312=expected_select313?{1'b0,expected_address313}:(load_enable312?read_base312+{6'd0,load_at315}:payload_base314+{2'd0,sn_address});", "wire [9:0] read_address312=expected_select313?{1'b0,expected_address313}:{1'b1,retired[0],(load_enable312?field338(load_at315):sn_address)};")
    a=s.index(' wire [9:0] ingress_base314=');b=s.index(' always @(posedge clk)if(write312)',a)
    s=s[:a]+''' wire [7:0] ingress_offset338=byte_count[7:0]-8'd1;
 wire write312=!reset&&!fault&&enable&&!ss[1]&&sck[1]&&!prev_sck&&
  bit_count==7&&command==8'he1&&can_write&&byte_count!=0&&byte_count<=256;
 wire [9:0] write_address312={1'b1,accepted[0],ingress_offset338};
 wire [7:0] write_data312=incoming;
'''+s[b:]
    s=once(s,'sequence312<=0;opcode312<=0;bad_header312<=0;','sequence312<=0;bad_header312<=0;')
    s=once(s,'        if(byte_count==1)opcode312<=incoming;\n','')
    s=once(s,"       end else if(byte_count<={4'd0,write_prefix312})begin\n        \n       end else begin end", '       end')
    p.write_text(s,newline='\n')
    p=d/'nes_transport257.sv';s=p.read_text()
    s=once(s,' reg [7:0] read_byte,snapshot_length,header_crc;\n reg [15:0] snapshot_crc,snapshot_token;\n reg snapshot_ready;', ''' reg [7:0] read_byte,header_crc;
 reg snapshot_ready;
 // The checked prefix selects a bank. Its mailbox stays immutable until POP.
 // Keep ready sampled: a bank published during an empty response is NOT read.
 wire [7:0] snapshot_length=snapshot_ready?length:8'd0;
 wire [15:0] snapshot_crc=checksum,snapshot_token=token;''')
    s=once(s,'snapshot_length<=0;snapshot_crc<=0;snapshot_token<=0;snapshot_ready<=0;', 'snapshot_ready<=0;')
    s=once(s,'snapshot_ready<=next_sealed;snapshot_length<=next_sealed?next_descriptor[23:16]:0;\n       snapshot_crc<=next_descriptor[15:0];snapshot_token<=token+request_flags[0];', 'snapshot_ready<=next_sealed;')
    p.write_text(s,newline='\n')
