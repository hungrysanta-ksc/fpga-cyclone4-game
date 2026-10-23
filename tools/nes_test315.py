# SPDX-License-Identifier: MIT
"""Drive the external common record reader in endpoint-only fixtures."""
from nes_delta231 import once

def reader(s,record,valid,at,byte,ready,retire,reset):
    s=once(s,".load_enable312(1'b1)", '.load_enable312(fetch315),.load_at315(index315)')
    needle=f'always @(posedge clk)if({valid}){record}[{at}*8+:8]<={byte};'
    s=once(s,needle,'reg fetch315=0,loaded315=0;reg [3:0] index315=0;')
    s=once(s,'endmodule',f'''
 always @(posedge clk)begin
  if({reset}||{retire})begin fetch315<=0;loaded315<=0;index315<=0;end
  else if(!loaded315&&!fetch315&&{ready})begin fetch315<=1;index315<=0;end
  else if(fetch315)begin
   if(index315==({record}[7:0]==14?15:{record}[7:0]==12?14:10))begin fetch315<=0;loaded315<=1;end
   else index315<=index315+1'b1;
  end
  if({valid})begin
   if({at}==0){record}[119:80]<=0;
   {record}[{at}*8+:8]<={byte};
  end
 end
endmodule''')
    return s
