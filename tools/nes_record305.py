# SPDX-License-Identifier: MIT
"""Active header/typed record and page-local independent receipt RAM walk."""
from nes_delta231 import once
import re

def apply(d):
 p=d/'nes_mux260.sv';s=p.read_text()
 s=once(s,'reg batch;reg [7:0] remaining;reg [8:0] cursor;','reg batch;reg [8:0] cursor;')
 s=once(s,'reg [7:0] header[0:20];reg [7:0] at,held,parser_address;', '''typedef struct packed {
  logic [7:0] op,section;logic [15:0] start,encoded,span;
  logic [31:0] token;logic [7:0] left;logic [16:0] endpos;
  logic [11:0] receipt_first,receipt_end;
 } active_t305;
 active_t305 active305;
 wire [7:0] remaining=active305.left;
 wire [7:0] header[0:20];
 assign header[0]=active305.op;assign header[1]=active305.section;
 assign header[10]=active305.start[7:0];assign header[11]=active305.start[15:8];
 assign header[12]=active305.encoded[7:0];assign header[13]=active305.encoded[15:8];
 assign header[14]=active305.span[7:0];assign header[15]=active305.span[15:8];
 assign header[16]=active305.token[7:0];assign header[17]=active305.token[15:8];
 assign header[18]=active305.token[23:16];assign header[19]=active305.token[31:24];
 assign header[20]=active305.left;
 reg [7:0] at,held,parser_address;''')
 s=once(s,'reg [11:0] length,first,count;reg [31:0] token;', "wire [11:0] length=active305.span[11:0],first=active305.start[12:1],count={1'b0,active305.span[11:1]};wire [31:0] token=active305.token;")
 s=s.replace('remaining<=','active305.left<=');s=re.sub(r'(?<![a-zA-Z0-9_])token<=','active305.token<=',s)
 s=s.replace('length<=0;first<=0;count<=0;','')
 s=once(s,'else header[at]<=qdata;', '''else case(at)
       0:active305.op<=qdata;1:active305.section<=qdata;
       10:active305.start[7:0]<=qdata;11:active305.start[15:8]<=qdata;
       12:active305.encoded[7:0]<=qdata;13:active305.encoded[15:8]<=qdata;
       14:active305.span[7:0]<=qdata;15:active305.span[15:8]<=qdata;
       16:active305.token[7:0]<=qdata;17:active305.token[15:8]<=qdata;
       18:active305.token[23:16]<=qdata;19:active305.token[31:24]<=qdata;
       20:active305.left<=qdata;default:;
      endcase ''')
 s=once(s,"wire [16:0] descriptor_end287={1'b0,startpos}+{1'b0,outlen};", "wire [16:0] decode_end305={1'b0,startpos}+{1'b0,outlen};\n wire [16:0] descriptor_end287=active305.endpos;")
 a=s.index(' reg bad_data278;');z=s.index(' // Capture only',a)
 raw=s[a:z].replace('descriptor_end287','decode_end305')
 raw=once(raw,'  if(header[1]==3&&', '''  if(header[1]==5&&decode_end305>1121&&
    ((startpos>1121&&startpos<3169&&(startpos-16'd1121)%16!=0)||
     (decode_end305<3169&&(decode_end305-17'd1121)%16!=0)))bad_data278=1;
  if(header[1]==3&&''')
 raw+=''' wire bad_tile305=header[1]>1||plen!=4||!outlen||outlen>2048||
  (header[1]==0?(startpos[3:0]!=0||outlen[3:0]!=0||decode_end305>16384):
   (startpos[4:0]!=0||outlen[4:0]!=0||decode_end305>4096));
 wire bad_internal305=header[0]==15?(manifest_phase!=0||qlen!=206||header[1]!=0||plen!=190||startpos!=0||outlen!=0):
  (header[0]==10||header[0]==11)?(manifest_phase!=1||header[1]!=2||startpos!=manifest_at||outlen!=0||plen==0):
  (manifest_phase!=1||manifest_at!=256||qlen!=16||plen!=0||startpos!=0||outlen!=0||header[1]!=0);
'''
 s=s[:a]+raw+s[z:]
 s=once(s,"wire [12:0] tap_end278={1'b0,startpos[11:0]}+{1'b0,outlen[11:0]};", 'wire [12:0] tap_end278=descriptor_end287[12:0];')
 a=s.index(' reg [11:0] receipt_first282;');z=s.index(' // One command handshake',a)
 raw=s[a:z].replace('receipt_first282','decoded_first305').replace('receipt_limit287','decoded_limit305').replace('receipt_valid282','decoded_valid305').replace('descriptor_end287','decode_end305').replace('if(state==OTILE||state==OSELECT)begin','begin')
 s=s[:a]+raw+''' wire [11:0] receipt_first282=active305.receipt_first,receipt_limit287=active305.receipt_end;
 wire receipt_valid282=(state==OTILE||state==OSELECT)&&receipt_limit287>receipt_first282;
'''+s[z:]
 s=once(s,'     CHECK:begin','''     CHECK:begin
      active305.endpos<=decode_end305;active305.receipt_first<=decoded_first305;active305.receipt_end<=decoded_limit305;''')
 s=once(s,'prelude_mode<=1;length<=32;','prelude_mode<=1;active305.span<=32;')
 s=once(s,'batch<=1;active305.left<=header[20];','batch<=1;')
 s=s.replace('active305.token<={header[19],header[18],header[17],header[16]};','')
 s=once(s,"if(plen+16'd16!={7'd0,qlen})failed<=1;else state<=OSETUP;", "if(plen+16'd16!={7'd0,qlen}||bad_internal305)failed<=1;else state<=XBEGIN298;")
 s=once(s,'||(data_command278&&bad_data278))failed<=1;','||(data_command278&&bad_data278)||(header[0]==7&&bad_tile305))failed<=1;')
 s=once(s,"batch<=0;first<={header[11][3:0],header[10]};length<={4'd0,header[14]};count<=header[14]>>1;", "batch<=0;active305.start<={startpos[14:0],1'b0};")
 s=once(s,'header[10+at]<=qdata;', '''case(at)
       0:active305.start[7:0]<=qdata;1:active305.start[15:8]<=qdata;
       2:active305.span<={8'd0,qdata};default:;
      endcase ''')
 a=s.index('     DCHECK:begin');z=s.index('     OPEN:',a)
 raw=s[a:z].replace('header[12]','header[14]')
 raw=once(raw,"first<={1'b0,header[11][3:0],header[10][7:1]};length<={4'd0,header[14]};count<=header[14]>>1;",'')
 s=s[:a]+raw+s[z:]
 a=s.index('     OSETUP:begin');z=s.index('     OTILE,OSELECT:',a)
 s=s[:a]+'''     OSETUP:begin
      if(header[0]==7)begin
       if(!tile_proven||pattern278!=token)failed<=1;else state<=OTILE;
      end else if(data_command278)state<=OSELECT;
      else failed<=1;
     end
'''+s[z:]
 assert 'header[at]<=' not in s and 'reg [7:0] header' not in s
 p.write_text(s,newline='\n')
 p=d/'nes_validator278.sv';s=p.read_text()
 s=once(s,'reg [9:0] cursor,v_addr;','reg map_phase305;reg [9:0] cursor,v_addr;')
 s=once(s,"assign manifest_at282=cursor>=166?cursor-10'd166:9'd0;", "assign manifest_at282=map_phase305?cursor[8:0]:9'd0;")
 s=once(s,'assign manifest_started282=rec_i!=0||cursor!=0;','assign manifest_started282=rec_i!=0||cursor!=0||map_phase305;')
 s=once(s,"v_addr=(v_mapmode?10'd768:10'd512)+{1'b0,v_bit_at[11:3]};", "v_addr={1'b1,v_mapmode,v_bit_at[10:3]};")
 s=once(s,"v_addr=v_validbase+{1'b0,v_bit_at[11:3]};", "v_addr={1'b0,v_bank,v_bit_at[10:3]};")
 s=once(s,"V_CHECKREAD,V_CHECKTEST:v_addr=cursor<144?v_validbase+cursor:cursor<166?10'd512+cursor:10'd768+cursor-10'd166;", "V_CHECKREAD,V_CHECKTEST:v_addr=map_phase305?{2'b11,cursor[7:0]}:cursor<144?{1'b0,v_bank,cursor[7:0]}:{2'b10,cursor[7:0]};")
 s=once(s,'V_PCHECKREAD,V_PCHECKTEST:v_addr=v_validbase+cursor;', "V_PCHECKREAD,V_PCHECKTEST:v_addr={1'b0,v_bank,cursor[7:0]};")
 s=once(s,"v_addr=hash_base+{5'd0,hash_index,1'b0}+(state==H_WRITEHI?10'd1:10'd0);", "v_addr={4'b0111,v_bank,hash_index,(state==H_WRITEHI)};")
 s=once(s,"v_addr=hash_base+{5'd0,h_count[4:0]};", "v_addr={4'b0111,v_bank,h_count[4:0]};")
 s=once(s,"begin cursor<=cursor+1'b1;if(executing298)", "begin if(!map_phase305&&cursor==165)begin cursor<=0;map_phase305<=1;end else cursor<=cursor+1'b1;if(executing298)")
 s=s.replace('cursor!=422','(!map_phase305||cursor!=256)').replace('cursor==422','(map_phase305&&cursor==256)').replace('cursor>=422','(map_phase305&&cursor>=256)')
 s=s.replace('cursor<144)begin','!map_phase305&&cursor<144)begin').replace('else if(cursor<166)begin','else if(!map_phase305&&cursor<166)begin')
 s=s.replace('cursor==0&&','!map_phase305&&cursor==0&&').replace('cursor!=0)fault','(map_phase305||cursor!=0))fault').replace('cursor!=0||','(map_phase305||cursor!=0)||')
 s=once(s,'   crc_mask287<=0;state<=V_CLEARALL;','   map_phase305<=0;crc_mask287<=0;state<=V_CLEARALL;')
 s=once(s,'else begin rec_i<=0;certificate_ok<=0;digest_ready<=0;','else begin map_phase305<=0;rec_i<=0;certificate_ok<=0;digest_ready<=0;')
 p.write_text(s,newline='\n')

def observe(s):
 s=s.replace('if(active263&&dut.flow.state==dut.flow.OSETUP)begin', 'if(active263&&dut.flow.state==dut.flow.XBEGIN298)begin')
 s=s.replace('if(dut.flow.state==dut.flow.OSETUP)begin parser_active264', 'if(dut.flow.state==dut.flow.OSETUP||dut.flow.state==dut.flow.XBEGIN298)begin parser_active264')
 return once(s,' task clear_output;', '''
 always @(posedge host_clk)if(!reset&&active263&&!source_fault)begin
  if($bits(dut.flow.active305)!=145)$fatal(1,"active record budget");
 end
 task clear_output;''')
