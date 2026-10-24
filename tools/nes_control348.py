# SPDX-License-Identifier: MIT
"""NES348 host executor + common ingress events/length, independent lifetimes."""
from nes_delta231 import once

def apply(d):
 from nes_execute346 import host
 host(d)
 p=d/'nes_spi270.sv';s=p.read_text()
 s=once(s,"(count>=19&&count<=259&&payload_crc280==0)","(count>=19&&count<=259&&payload_crc280==0&&request_length280=={6'd0,count}-16'd19)")
 s=once(s,"   if(command==8'hd4||command==8'hd5)begin", "   if(command==8'he1)begin\n    if(count==13)request_length280[7:0]<=incoming;\n    if(count==14)request_length280[15:8]<=incoming;\n   end else if(command==8'hd4||command==8'hd5)begin")
 p.write_text(s,newline='\n')
 p=d/'nes_queue260.sv';s=p.read_text()
 s=once(s,'reg [15:0] sequence312,ingress_length312;', 'reg [15:0] sequence312;')
 s=once(s,'   ingress_length312<=0;','')
 s=once(s,"||ingress_length312!={7'd0,byte_count}-16'd19",'')
 s=once(s,'        if(byte_count==13)ingress_length312[7:0]<=incoming;\n        if(byte_count==14)ingress_length312[15:8]<=incoming;','')
 s=once(s,"wire write312=!reset&&!fault&&enable&&!ss[1]&&sck[1]&&!prev_sck&&\n  bit_count==7&&command", "wire write312=!reset&&!fault&&enable&&link270[110]&&command")
 s=once(s,'   if(ss[1])begin\n    \n    if(link270[109]&&ours)begin', '   if(link270[109]&&ours)begin')
 s=once(s,"    end\n   end else if(sck[1]&&!prev_sck)begin\n    \n    if(bit_count==7)begin", '   end else if(link270[110])begin')
 s=once(s,'    end\n   end\n  end\n end\n\n assign crc_take270', '   end\n  end\n end\n\n assign crc_take270')
 p.write_text(s,newline='\n')
 p=d/'nes_plan_spi200.sv';s=p.read_text()
 s=once(s,'   if(ss[1])begin\n    \n    if(link270[109]&&ours)begin', '   if(link270[109]&&ours)begin')
 s=once(s,'    end\n   end else if(link270[110])begin\n    \n    if(bits==7)begin', '   end else if(link270[110])begin')
 s=once(s,'    end\n   end\n  end\n end\n\n assign crc_take270', '   end\n  end\n end\n\n assign crc_take270')
 p.write_text(s,newline='\n')

 from nes_plan348 import apply as normalize
 normalize(d)
