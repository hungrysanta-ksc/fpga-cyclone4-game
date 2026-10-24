# SPDX-License-Identifier: MIT
"""Shared request lifetime, plan seal fields and slot address ownership."""
from nes_delta231 import once


def fsm(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    states=('MREAD313','MCAP313','MNEXT313','MISSUE313','MWAIT313','MDONE313',
            'MHASH313','MHASHWAIT313','MCERT313','MCERTWAIT313','MFINISH313','MSEALWAIT313')
    s=once(s,'state>=MREAD313&&state<=MSEALWAIT313','('+'||'.join('state=='+x for x in states)+')')
    p.write_text(s,newline='\n')


def plan_cursor(d):
    p=d/'nes_plan_batch206.sv'
    if p.exists():
        s=p.read_text()
        s=once(s,'count,batch_length,offset;', 'count,batch_length,read_cursor314;')
        s=s.replace('offset+{4\'d0,at}','read_cursor314')
        s=s.replace('offset+{4\'d0,length}',"read_cursor314+10'd1")
        s=s.replace('offset<=0;', 'read_cursor314<=0;')
        s=once(s,"offset<=read_cursor314+10'd1;", "read_cursor314<=read_cursor314+10'd1;")
        s=once(s,"else begin at<=at+1'b1;state<=READ;end", "else begin at<=at+1'b1;read_cursor314<=read_cursor314+1'b1;state<=READ;end")
        assert 'offset' not in s
        p.write_text(s,newline='\n')


def apply(d):
    fsm(d)
    plan_cursor(d)
    for p in d.glob('*.sv'):
        s=p.read_text().replace('[109:0]','[112:0]');p.write_text(s,newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'wire request_step=byte_event&&request_crc_enable;', '''wire plan_payload314=command==8'he9&&count>=4&&count<=request_length280+3;
 wire request_step=byte_event&&request_crc_enable;''')
    # Strict declaration ordering: the shared predicate references length.
    s=s.replace(" wire plan_payload314=command==8'he9&&count>=4&&count<=request_length280+3;\n",'')
    s=once(s,'reg crc_good280,tail_good280;', '''reg crc_good280,tail_good280;
 wire plan_payload314=command==8'he9&&count>=4&&count<=request_length280+3;
 assign link[110]=byte_event;
 assign link[111]=plan_payload314;
 assign link[112]=command==8'he9&&count==3&&
  (request_length280<3||request_length280>512||incoming==0||incoming>16);''')
    s=once(s,"(command==8'he9&&count>=4&&count<=request_length280+3)",'plan_payload314')
    s=once(s,'''end else if(ss[1])begin
   request_length280<=0;request_value280<=0;request_number280<=0;
   crc_good280<=0;tail_good280<=0;payload_crc280<=16'hffff;
  end else if(byte_event)begin''','''end else if(ss[1])begin
   // The sealed request fields outlive SS for the next-cycle RAM handoff.
   crc_good280<=0;tail_good280<=0;payload_crc280<=16'hffff;
  end else if(byte_event)begin
   if(count==0)begin request_length280<=0;request_value280<=0;request_number280<=0;end''')
    p.write_text(s,newline='\n')
    p=d/'nes_plan_spi200.sv';s=p.read_text()
    s=once(s,'output reg plan_seal,output reg [9:0] plan_length,output reg [4:0] plan_plans,output reg [15:0] plan_crc,',
           'output reg plan_seal,output wire [9:0] plan_length,output wire [4:0] plan_plans,output wire [15:0] plan_crc,')
    s=once(s,'wire [15:0] received16=link270[90:75];reg [15:0] accepted;', '''wire [15:0] received16=link270[90:75];reg [15:0] accepted;
 assign plan_length=length[9:0];assign plan_plans=number[4:0];assign plan_crc=received16;''')
    s=once(s,';plan_length<=0;plan_plans<=0;plan_crc<=0;',';')
    s=once(s,"plan_length<=length[9:0];plan_plans<=number[4:0];plan_crc<=received16;plan_seal<=1;",'plan_seal<=1;')
    s=once(s,"if(length<3||length>512||incoming==0||incoming>16)fault<=1;",'if(link270[112])fault<=1;')
    s=once(s,'else if(count>=4&&count<=length+3)begin','else if(link270[111])begin')
    s=once(s,'end else if(sck[1]&&!prev_sck)begin','end else if(link270[110])begin')
    p.write_text(s,newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text()
    old="read_base312+(loading312?{5'd0,load_at312}:10'd24+{2'd0,sn_address}-{5'd0,prefix312})"
    new="(loading312?read_base312+{5'd0,load_at312}:payload_base314+{2'd0,sn_address})"
    s=once(s,old,new)
    s=once(s,'wire [7:0] head_op312=record312[7:0];', '''wire [7:0] head_op312=record312[7:0];
 wire [9:0] payload_base314=retired[0]?
  (head_op312==14?10'd755:head_op312==12?10'd756:10'd760):
  (head_op312==14?10'd483:head_op312==12?10'd484:10'd488);
 wire [9:0] ingress_base314=byte_count<={4'd0,write_prefix312}?
  (accepted[0]?10'd745:10'd473):accepted[0]?
  (opcode312==14?10'd754:opcode312==12?10'd755:10'd759):
  (opcode312==14?10'd482:opcode312==12?10'd483:10'd487);''')
    # Move ingress predicate below declarations it references.
    a=s.index(' wire [9:0] ingress_base314=');b=s.index(';',a)+1
    wire=s[a:b];s=s[:a]+s[b:]
    s=once(s,' reg write312;',wire+'\n reg write312;')
    s=once(s,"if(byte_count<={4'd0,write_prefix312})write_address312=write_base312+byte_count-7;\n     else write_address312=write_base312+10'd24+byte_count-1'b1-{5'd0,write_prefix312};",
           "write_address312=ingress_base314+{1'b0,byte_count};")
    p.write_text(s,newline='\n')
