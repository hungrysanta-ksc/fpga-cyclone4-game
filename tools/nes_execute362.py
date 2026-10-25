# SPDX-License-Identifier: MIT
"""Bounded common host-clock CRC execution, after repaired358 + host359.

Deletes both local CRC combinational implementations. Independent accumulators,
expected data and receipt publication remain. This is NOT a full FSM replacement.
"""
from nes_delta231 import once

def apply(d):
 for name in ('nes_core257','nes_validator278'):
  p=d/(name+'.sv');s=p.read_text()
  s=once(s,'module '+name+'(', 'module '+name+'(output wire [23:0] crc_args362,input wire [15:0] crc_shared362,')
  a=s.index(' function automatic [15:0] crc16(');b=s.index(' endfunction',a)+len(' endfunction')
  s=s[:a]+s[b:]
  if name=='nes_core257':
   s=once(s,'assign crc_result=crc16(crc_previous,crc_byte);','assign crc_args362={crc_previous,crc_byte};\n assign crc_result=crc_shared362;')
  else:
   s=once(s,'wire [15:0] crc_result=crc16(checksum,crc_byte);','assign crc_args362={checksum,crc_byte};\n wire [15:0] crc_result=crc_shared362;')
  p.write_text(s,newline='\n')
 p=d/'nes_joint257.sv';s=p.read_text()
 a=s.index('nes_core257 encoder')
 s=s[:a]+'''wire [23:0] source_crc362,check_crc362;
 wire [23:0] crc_args362=output_phase?check_crc362:source_crc362;
 function automatic [15:0] crc16_362(input [23:0] args);
  reg [15:0] c;integer i;begin c=args[23:8]^{args[7:0],8'd0};
   for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;
   crc16_362=c;end
 endfunction
 wire [15:0] crc_shared362=crc16_362(crc_args362);
 '''+s[a:]
 s=once(s,'nes_core257 encoder(', 'nes_core257 encoder(.crc_args362(source_crc362),.crc_shared362(crc_shared362),')
 s=once(s,'nes_validator278 validator(', 'nes_validator278 validator(.crc_args362(check_crc362),.crc_shared362(crc_shared362),')
 p.write_text(s,newline='\n')
