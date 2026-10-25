# SPDX-License-Identifier: MIT
"""Canonical expected bytes in queue RAM; late independent coverage walk."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'input wire parser_retire,', '''input wire expected_select313,expected_write313,
 input wire [8:0] expected_address313,input wire [7:0] expected_data313,
 input wire parser_retire,''')
    s=once(s,'wire [9:0] read_address312=read_base312+', "wire [9:0] read_address312=expected_select313?{1'b0,expected_address313}:read_base312+")
    s=once(s,'always @(posedge clk)read_data<=buffer[read_address312];', '''always @(posedge clk)begin
  read_data<=buffer[read_address312];
  if(expected_write313&&expected_select313&&expected_address313<446&&enable&&!reset&&!fault)
   buffer[read_address312]<=expected_data313;
 end''')
    s=once(s,'assign sn_data=virtual312;', 'assign sn_data=expected_select313?read_data:virtual312;')
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'reg display_byte313;', '''reg display_byte313,requirements_complete313;
 reg [8:0] map_received313;
 wire canonical_read313=header[0]==3&&metadata313;
 wire canonical_write313=header[0]!=3&&state==MISSUE313&&!rst&&!fault;
 wire [8:0] canonical_address313=canonical_read313?manifest_byte313:
  display_byte313?parser_address-9'd17:
  header[0]==15?manifest_byte313+9'd24:manifest_byte313+9'd190;''')
    # Move expressions after declarations they reference, for strict Verilog.
    a=s.index(' wire canonical_read313=');b=s.index('\n ',s.index("header[0]==15?manifest_byte313+9'd24:manifest_byte313+9'd190;",a))
    wires=s[a:b];s=s[:a]+s[b:]
    s=once(s,' wire [7:0] qaddr=',wires+'\n wire [7:0] qaddr=')
    s=once(s,'nes_queue260 queue(', '''nes_queue260 queue(.expected_select313(canonical_read313||canonical_write313),
 .expected_write313(canonical_write313),.expected_address313(canonical_address313),.expected_data313(held),''')
    s=once(s,'wire [8:0] manifest_at=manifest_at282;', 'wire [8:0] manifest_at=map_received313;')
    s=once(s,'sealed?2\'d2:manifest_started282?2\'d1:2\'d0;', "sealed?2'd2:requirements_complete313?2'd1:2'd0;")
    s=s.replace('      else if(manifest_phase!=0&&header[0]!=10&&header[0]!=11&&header[0]!=3)failed<=1;\n','')
    s=once(s,'if(manifest_phase!=0||!outlen||', 'if(sealed||!outlen||')
    s=s.replace('assign display_write=state==MISSUE313&&', 'assign display_write=canonical_read313&&state==MISSUE313&&')
    s=s.replace('assign ordinary_check=state==MISSUE313&&', 'assign ordinary_check=canonical_read313&&state==MISSUE313&&')
    s=once(s,'manifest_byte313<=0;display_byte313<=0;', 'manifest_byte313<=0;display_byte313<=0;requirements_complete313<=0;map_received313<=0;')
    s=once(s,'have_identity<=1;prelude_done<=0;', 'have_identity<=1;requirements_complete313<=0;map_received313<=0;prelude_done<=0;')
    s=once(s,'manifest_byte313<=header[0]==15?0:manifest_at;', 'manifest_byte313<=(header[0]==15||header[0]==3)?0:manifest_at;')
    s=once(s,'state<=header[0]==3?MHASH313:MREAD313;', 'state<=MREAD313;')
    s=once(s,"if({1'b0,parser_address}>=qlen)failed<=1;", '''if(header[0]==3)begin
       held<=qdata;display_byte313<=manifest_byte313<24;state<=MISSUE313;
      end else if({1'b0,parser_address}>=qlen)failed<=1;''')
    s=once(s,'MISSUE313:if(range_ready)state<=MWAIT313;', '''MISSUE313:if(range_ready)begin
      if(!canonical_read313&&canonical_address313>=446)failed<=1;
      else state<=MWAIT313;
     end''')
    s=once(s,'''if(!display_byte313)manifest_byte313<=manifest_byte313+1'b1;
      state<=MNEXT313;''', '''if(header[0]==3)begin
       if(manifest_byte313==445)state<=MHASH313;
       else begin manifest_byte313<=manifest_byte313+1'b1;state<=MREAD313;end
      end else begin
       if(!display_byte313)manifest_byte313<=manifest_byte313+1'b1;
       state<=MNEXT313;
      end''')
    s=once(s,"MDONE313:begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;end", '''MDONE313:begin
      if(header[0]==15)requirements_complete313<=1;
      else if(header[0]==10||header[0]==11)map_received313<=manifest_byte313;
      qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;
     end''')
    p.write_text(s,newline='\n')
