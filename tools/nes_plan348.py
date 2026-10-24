# SPDX-License-Identifier: MIT
"""Streaming E9 normalization into existing16x32B slots; wire remains packed."""
from nes_delta231 import once

def apply(d):
 p=d/'nes_plan_batch206.sv';s=p.read_text()
 s=once(s,'reg [5:0] at,length;', 'reg [5:0] at;wire [5:0] length=32;')
 s=once(s,'.src_data({writer,count,plans})',".src_data({writer,plans,5'b0,plans})")
 s=once(s,'&&count<512;', '&&count<512&&!clear348&&hplans348<16;')
 a=s.index(' always @(posedge host_clk)if(write_valid');b=s.index(' always @(posedge host_clk or posedge hr)',a)
 s=s[:a]+''' reg [4:0] hplans348,clear_at348;
 reg [5:0] hat348,hlen348;
 reg hshort348,hbad348,clear348;reg [1:0] hkind348;
 reg [7:0] hmask348;reg [3:0] halt348;
 reg [4:0] dest348;reg [7:0] value348;
 function automatic [3:0] count348(input [7:0] b);
  integer j;begin count348=0;for(j=0;j<8;j=j+1)count348=count348+b[j];end
 endfunction
 function automatic [3:0] next348(input [7:0] b,input [3:0] first);
  integer j;begin next348=8;for(j=7;j>=0;j=j-1)if(j>=first&&b[j])next348=j;end
 endfunction
 always @*begin
  dest348=hat348[4:0];value348=write_data;
  if(hat348==0)begin dest348=0;value348=write_data[7]?{5'd0,write_data==8'h87,write_data[1:0]}:write_data;end
  else if(hshort348)begin
   case(hat348)
    1:dest348=2;2:dest348=3;3:dest348=4;4:dest348=5;5:dest348=6;6:dest348=7;default:dest348=8;
   endcase
  end else if(hat348>=16)dest348=5'd16+{halt348[2:0],1'b0}+hat348[0];
  if(clear348)begin
   dest348=clear_at348;value348=0;
   if(clear_at348==15)value348=1;
   if(hshort348&&!hkind348[1])case(clear_at348)
    8:value348=255;9:value348=8'h40;10:value348=8'h22;11:value348=8'h6d;
    12:value348=8'h64;13:value348=8'h6b;14:value348=8'hff;default:;
   endcase
  end
 end
 always @(posedge host_clk)if(!hc&&(clear348||(write_valid&&write_ready)))
  payload[{writer,hplans348[3:0],dest348}]<=value348;
 always @(posedge host_clk or posedge hr)begin
  if(hr)begin hplans348<=0;hat348<=0;hlen348<=16;hshort348<=0;hkind348<=0;hmask348<=0;halt348<=0;hbad348<=0;clear348<=0;clear_at348<=0;end
  else if(!hc)begin
   if(clear348)begin
    if(clear_at348==31)clear348<=0;else clear_at348<=clear_at348+1'b1;
   end
   if(write_valid&&write_ready)begin
    if(hat348==0)begin
     hshort348<=write_data[7];hkind348<=write_data[1:0];hmask348<=0;halt348<=0;
     if(write_data[7])begin
      if(write_data[6:2]!=0&&write_data!=8'h87)hbad348<=1;
      hlen348<=write_data[1]?3:write_data[0]?8:7;
     end else begin hlen348<=16;if(write_data[7:2]!=0)hbad348<=1;end
     clear348<=1;clear_at348<=1;
    end
    if(hat348==1&&!hshort348)begin hmask348<=write_data;hlen348<=16+{count348(write_data),1'b0};end
    if(hat348==15&&!hshort348)halt348<=next348(hmask348,0);
    if(hat348>=16&&!hshort348)begin
     if(halt348>=8)hbad348<=1;
     if(hat348[0])halt348<=next348(hmask348,halt348+1'b1);
    end
    if(hat348!=0&&hat348+1==hlen348)begin hat348<=0;hplans348<=hplans348+1'b1;end
    else hat348<=hat348+1'b1;
   end
   if(pending&&box_ready)begin hplans348<=0;hat348<=0;hbad348<=0;end
  end
 end
''' +s[b:]
 s=once(s,'if(pending||write_valid||count<3', 'if(pending||write_valid||clear348||hbad348||hat348!=0||hplans348!=seal_plans||count<3')
 s=once(s,'reg bad,shortform,closed', 'reg bad,closed')
 s=once(s,'reg [3:0] alt_index;', '')
 a=s.index(' function automatic [3:0] popcount');b=s.index('  read_cursor314+10',a)
 s=s[:a]+" wire shape_ok=!bad&&\n"+s[b:]
 s=s.replace(';length<=0;',';').replace('length<=16;','').replace('alt_index<=0;','').replace('shortform<=0;','')
 s=once(s,'     else if(at>=16&&alt_index>=8)nf<=1;\n     else if(at>=16&&!plan_alt_mask[alt_index])alt_index<=alt_index+1\'b1;','')
 a=s.index('     if(at==0&&data[7])begin');b=s.index('     case(at)',a)
 # skip shortform case and retain full-field case
 b=s.index('     case(at)',b+1) if s[b:s.index('endcase',b)].find('plan_generation[7:0]<=data')>=0 and '1:plan_generation' in s[b:s.index('endcase',b)] else b
 # Find unambiguous full-field case beginning with kind capture.
 b=s.index('     case(at)\n      0:begin plan_kind',a)
 s=s[:a]+s[b:]
 s=once(s,"0:begin plan_kind<=data[1:0];partial295<=0;if(data[7:2]!=0)bad<=1;end", "0:begin plan_kind<=data[1:0];partial295<=data==7;if(data[7:2]!=0&&data!=7)bad<=1;end")
 s=once(s,"1:begin plan_alt_mask<=data;length<=16+{popcount(data),1'b0};end",'1:plan_alt_mask<=data;')
 s=once(s,"default:if(!at[0])alt[alt_index][7:0]<=data;\n              else begin alt[alt_index][12:8]<=data[4:0];if(data[7:5]!=0)bad<=1;alt_index<=alt_index+1'b1;end", "default:if(!at[0])alt[at[3:1]][7:0]<=data;\n              else begin alt[at[3:1]][12:8]<=data[4:0];if(data[7:5]!=0)bad<=1;end")
 s=once(s,'     endcase\n     end\n     if(at==length-1)', '     endcase\n     if(at==length-1)')
 for dead in ('shortform','alt_index','popcount',';length<='):assert dead not in s,dead
 a=s.index(' reg [4:0] hplans348');b=s.index(' function automatic [3:0] count348',a)
 decl=s[a:b];s=s[:a]+s[b:];s=once(s,' reg pending,writer',decl+' reg pending,writer')
 p.write_text(s,newline='\n')
