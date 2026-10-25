# SPDX-License-Identifier: MIT
"""Replace338 queue field adapter with skip-header/common host RAM reader."""
from nes_delta231 import once

def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'input wire [15:0] frame_generation312,input wire [191:0] record312,input wire load_enable312,input wire [3:0] load_at315,output wire storage_empty312,\n output wire record_valid312,output wire [4:0] record_at312,output wire [7:0] record_byte312,',
        'input wire [15:0] frame_generation312,output wire storage_empty312,output wire head_bank351,')
    s=once(s,'input wire expected_select313,expected_write313,\n input wire [8:0] expected_address313,input wire [7:0] expected_data313,',
        'input wire expected_write313,input wire [7:0] expected_data313,')
    s=once(s,'input wire [7:0] sn_address,output wire [7:0] sn_data,','input wire [9:0] read_address351,output wire [7:0] sn_data,')
    s=once(s,'output wire packet_ready,output wire [8:0] packet_length,','output wire packet_ready,')
    a=s.index(' wire [15:0] encoded312=');b=s.index(' function automatic [7:0] identity312',a)
    s=s[:a]+s[b:]
    a=s.index(' wire [7:0] read_address=');b=s.index(' always @(posedge clk)begin',a)
    s=s[:a]+" assign head_bank351=retired[0];\n"+s[b:]
    s=s.replace('buffer[read_address312]','buffer[read_address351]')
    s=once(s,'expected_write313&&expected_select313&&expected_address313<472','expected_write313&&read_address351<472')
    a=s.index(' assign record_valid312=');b=s.index(' assign sn_data=',a);s=s[:a]+s[b:]
    s=once(s," assign packet_length=packet_ready?encoded312[8:0]+9'd16:9'd0;\n",'')
    p.write_text(s,newline='\n')

    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'DREAD=17,DCAP=18,','')
    s=once(s,'MREAD313=42,MCAP313=43,','MREAD313=42,')
    s=once(s,' reg [7:0] at,held;reg [8:0] parser_address;', ''' reg [7:0] at,held; reg [8:0] parser_address;
 reg [1:0] read_kind351;
 reg header_pending351;reg [4:0] return_addr351;
 task read_packet351(input [1:0] kind);
 begin read_kind351<=kind;state<=(kind==2&&header[0]==3)?MREAD313:PREAD;end
 endtask
 task advance_packet351;
 begin parser_address<=parser_address+1'b1;end
 endtask''')
    s=once(s,'state==MCAP313','((state==PREAD||state==PCAP)&&read_kind351==2)')
    a=s.index(' wire [7:0] qaddr=');b=s.index(' nes_queue260 queue(',a)
    s=s[:a]+''' wire head_bank351,storage_empty312;
 wire [9:0] ram_address351=(canonical_read313||canonical_write313)?
  {1'b0,canonical_address313}:{1'b1,head_bank351,parser_address[7:0]};
 assign queue_length312=qr?active305.encoded[8:0]+9'd16:9'd0;
 wire [127:0] progress_status;
'''+s[b:]
    s=once(s,'.expected_select313(canonical_read313||canonical_write313),','')
    s=once(s,'.expected_write313(canonical_write313),.expected_address313(canonical_address313),','.expected_write313(canonical_write313),')
    s=once(s,'.frame_generation312(identity[47:32]),.record312(record312),.load_enable312(state==HLOAD315),.load_at315(at[3:0]),','.frame_generation312(identity[47:32]),.head_bank351(head_bank351),')
    s=once(s,'.storage_empty312(storage_empty312),.record_valid312(record_valid312),.record_at312(record_at312),.record_byte312(record_byte312),','.storage_empty312(storage_empty312),')
    s=once(s,'.sn_address(qaddr),','.read_address351(ram_address351),')
    s=once(s,'.packet_length(queue_length312),','')
    s=once(s,'   prelude_mode<=0;prelude_done<=0;begun<=0;',"   read_kind351<=0;header_pending351<=0;return_addr351<=0;\n   prelude_mode<=0;prelude_done<=0;begun<=0;")
    a=s.index('   if(record_valid312&&!fault)begin');b=s.index('   if(iv&&can_admit)',a)
    s=s[:a]+'''   header_pending351<=state==HLOAD315&&!fault;
   if(state==HLOAD315&&!fault)begin
    return_addr351<=parser_address[4:0];
    if(header_pending351)case(return_addr351)
     0:begin active305.op<=qdata;active305.token<=0;active305.left<=0;end
     1:active305.section<=qdata;
     2:if(qdata!=packet_seq[7:0])failed<=1;
     3:if(qdata!=packet_seq[15:8])failed<=1;
     10:active305.start[7:0]<=qdata;11:active305.start[15:8]<=qdata;
     12:active305.encoded[7:0]<=qdata;13:active305.encoded[15:8]<=qdata;
     14:active305.span[7:0]<=qdata;15:active305.span[15:8]<=qdata;
     16:active305.token[7:0]<=qdata;17:active305.token[15:8]<=qdata;
     18:active305.token[23:16]<=qdata;19:active305.token[31:24]<=qdata;
     20:active305.left<=qdata;
     default:;
    endcase
   end
'''+s[b:]
    s=once(s,'at<=0;state<=HLOAD315;', 'at<=0;parser_address<=0;state<=HLOAD315;')
    s=once(s,'''     HLOAD315:begin
      if(at==(header[0]==14?15:header[0]==12?14:10))state<=HCHECK315;
      else at<=at+1'b1;
     end''', '''     HLOAD315:begin
      if(header_pending351&&return_addr351==(header[0]==14?20:header[0]==12?19:15))state<=HCHECK315;
      else parser_address<=parser_address==3?9'd10:parser_address+1'b1;
     end''')
    # Three packet consumers now share the actual request/return states.
    a=s.index('     DREAD:state<=DCAP;');b=s.index('     DCHECK:',a)
    desc=s[a:b].split('     DCAP:begin\n',1)[1].rsplit('     end\n',1)[0]
    s=s[:a]+s[b:]
    a=s.index('     MCAP313:begin\n');b=s.index('     MISSUE313:',a)
    meta=s[a:b].split('     MCAP313:begin\n',1)[1].rsplit('     end\n',1)[0]
    s=s[:a]+s[b:]
    s=once(s,'     PCAP:begin\n', '     PCAP:begin\n      if(read_kind351==1)begin\n'+desc+'      end else if(read_kind351==2)begin\n'+meta+'      end else begin\n')
    s=once(s,'     TILEWAIT313:', '     end\n     TILEWAIT313:')
    s=once(s,'MREAD313:if(header[0]!=3)state<=MCAP313;else if(range_ready)', 'MREAD313:if(range_ready)')
    for old,kind in [('state<=PREAD;',0),('state<=DREAD;',1),('state<=MREAD313;',2)]:
        s=s.replace(old,f'read_packet351(2\'d{kind});')
    s=s.replace("parser_address<=parser_address+1'b1;","advance_packet351();")
    s=once(s,' task advance_packet351;\n begin advance_packet351();end',' task advance_packet351;\n begin parser_address<=parser_address+1\'b1;end')
    assert all(x not in s for x in ('record_valid312','record_at312','record_byte312','DCAP','DREAD','MCAP313'))
    p.write_text(s,newline='\n')
