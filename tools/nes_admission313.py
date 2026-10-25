# SPDX-License-Identifier: MIT
"""Remove the last BEGIN/tile raw SNES packet view and ordered ACK relay."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    a=s.index(' reg [7:0] virtual312;');b=s.index(' assign record_valid312=',a)
    s=s[:a]+s[b:]
    s=once(s,'assign sn_data=expected_select313?read_data:virtual312;', 'assign sn_data=read_data;')
    p.write_text(s,newline='\n')

    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'localparam NONE=0', 'localparam TILEWAIT313=54;\n localparam NONE=0')
    s=once(s,'wire consume_record312=!rst&&!fault&&(\n  (state==CONSUME&&(!batch||remaining==1))||\n  (state==XWAIT298&&range_ready&&header[0]==7));',
           'wire consume_record312=!rst&&!fault&&state==CONSUME&&(!batch||remaining==1);')
    a=s.index(' wire ack_write=');b=s.index(' wire display_address=',a)
    s=s[:a]+" assign qdone=1'b0;\n"+s[b:]
    s=once(s,'wire [7:0] qaddr=state==NORMAL?asyn[7:0]:parser_address;', 'wire [7:0] qaddr=parser_address[7:0];')
    s=once(s,'((state==NORMAL&&qr)||(state==DMA&&data_command278&&chunk_ready))', '(state==DMA&&data_command278&&chunk_ready)')
    a=s.index('   if(state==NORMAL&&header[0]==7&&!tap_seen278');b=s.index('   if(tap_capture278)',a)
    s=s[:a]+s[b:]
    s=once(s,'(state==OTILE||state==OSELECT||(state==SEND&&data_command278))', '(state==SEND&&(data_command278||header[0]==7))')
    s=once(s,'assign range_valid=state==SEND&&!data_command278&&', 'assign range_valid=state==SEND&&!data_command278&&header[0]!=7&&')
    s=once(s,'assign map_consume=state==CONSUME&&!rst&&!fault;', 'assign map_consume=state==CONSUME&&owner==MAP&&!rst&&!fault;')
    s=once(s,"address[23:8]==16'h4000 ? qdata : aperture_data", 'aperture_data')
    s=once(s,"(ordinary_ready&&address[23:8]==16'h4000&&{1'b0,address[7:0]}<qlen&&qtag==address)||!aoe", '!aoe')
    s=once(s,'if(range_idle295&&!chunk_ready)begin owner<=NONE;end',
           'if(range_idle295&&!chunk_ready&&!(header[0]==7&&state!=IDLE))begin owner<=NONE;end')
    a=s.index('    if(tile_consume)begin');b=s.index('    if(!invalidate_banks&&rs&&!rp&&display_read)',a)
    s=s[:a]+'''    if(tile_consume)begin
     if(state!=DMA||header[0]!=7||token!=chunk_token)failed<=1;
     else state<=SEND;
    end
'''+s[b:]
    a=s.index("     if(ap>=24'h006010");b=s.index("     if(ap>=24'h00604c",a)
    s=s[:a]+s[b:]
    target='else begin ordinary_reads<=0;tile_proven<=0;at<=0;state<=NORMAL;end'
    s=once(s,'else if(header[0]!=12)begin\n',
           'else if(header[0]!=12)begin\n       if(!data_command278&&header[0]!=7)failed<=1;\n       else ')
    assert s.count(target)==2
    s=s.replace(target,'else begin batch<=0;at<=0;parser_address<=16;state<=PREAD;end')
    s=once(s,'PCAP:begin held<=qdata;state<=PUT;end', '''PCAP:begin
      if(header[0]==1)begin
       case(at)
        0:if(qdata!=8'h72)failed<=1;
        1:if(qdata!=8'h24)failed<=1;
        2:if(qdata!={7'd0,identity[48]})failed<=1;
        4,5,6,7:if(qdata!=previous_serial313[8*(at-4)+:8])failed<=1;
        8:if(qdata!=1)failed<=1;
        default:if(qdata!=0)failed<=1;
       endcase
       if(at==11)begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=BSTART;end
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else if(header[0]==7)begin
       active305.token[at[1:0]*8+:8]<=qdata;
       if(at==3)state<=TILEWAIT313;
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;state<=PREAD;end
      end else begin held<=qdata;state<=PUT;end
     end
     TILEWAIT313:if(owner==TILE&&chunk_ready)begin
      if(token!=chunk_token||header[1]!={7'd0,tkind}||length!=chunk_length||
         startpos!=({6'd0,tslot}<<(tkind?5:4)))failed<=1;
      else begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=DMA;end
     end''')
    s=once(s,'wire [15:0] startpos=', "wire [31:0] previous_serial313=identity[31:0]-1'b1;\n wire [15:0] startpos=")
    s=once(s,'if(!data_command278)begin last_map_token<=token;', 'if(header[0]==12||header[0]==14)begin last_map_token<=token;')
    a=s.index('     ACKWAIT:');b=s.index('     XBEGIN298:',a)
    s=s[:a]+s[b:]
    s=once(s,'if(header[0]==12||header[0]==14||data_command278)state<=CONSUME;', 'if(header[0]==12||header[0]==14||header[0]==7||data_command278)state<=CONSUME;')
    s=once(s,'else begin owner<=NONE;\n       if(batch)',
           'else begin owner<=header[0]==7&&(!range_idle295||chunk_ready)?TILE:NONE;\n       if(batch)')
    p.write_text(s,newline='\n')


def observe(s):
    if 'reg released312=0;' in s:
        s=once(s,'reg released312=0;reg [144:0] active312;', 'reg released312=0;reg [144:0] active312;reg [1:0] owner313;')
        s=once(s,'dut.flow.qretire&&dut.flow.header[0]==14', 'dut.flow.qretire&&(dut.flow.header[0]==14||dut.flow.header[0]==7||dut.flow.data_command278)')
        s=once(s,'released312<=1;active312<=dut.flow.active305;', 'released312<=1;active312<=dut.flow.active305;owner313<=dut.flow.owner;')
        s=once(s,'dut.flow.owner!=2)', 'dut.flow.owner!=owner313)')
    s=once(s,'dut.flow.good_consume&&dut.flow.data_command278', 'dut.flow.good_consume&&(dut.flow.data_command278||dut.flow.header[0]==7)')
    s=once(s,' task ordinary_task263;', '''
 integer admission_ignore313;reg [7:0] admission_byte313;
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.flow.state==dut.flow.CHECK&&(dut.flow.header[0]==1||dut.flow.header[0]==7))begin
   for(integer i=0;i<16;i++)begin
    if(i>=4&&i<=9)admission_byte313=i<8?dut.flow.identity[(i-4)*8+:8]:dut.flow.identity[32+(i-8)*8+:8];
    else if(i==2)admission_byte313=dut.flow.packet_seq[7:0];
    else if(i==3)admission_byte313=dut.flow.packet_seq[15:8];
    else admission_byte313=dut.flow.header[i];
    admission_ignore313=call263(1,i,admission_byte313);
   end
  end
  if(dut.flow.state==dut.flow.PCAP&&(dut.flow.header[0]==1||dut.flow.header[0]==7))
   admission_ignore313=call263(1,16+dut.flow.at,dut.flow.qdata);
  if(dut.flow.state==dut.flow.BSTART&&v_ready)begin admission_ignore313=call263(2,28,0);ordinary263++;end
 end
 task tile_consumer313;
 integer n313,ignore313,done313;reg [7:0] byte313;reg [31:0] token313;
 begin
  n313=dut.flow.chunk_length;token313=dut.flow.chunk_token;done313=dut.flow.queue.consumed312;
  #41904;
  for(integer i=0;i<n313;i++)begin rd261(24'h400800+i,byte313);ignore313=call263(5,i,byte313);end
  ignore313=call263(2,dut.flow.qlen,0);
  token261(token313);wr261(24'h006050,8'ha5);
  wait(dut.flow.queue.consumed312!=done313);
  tilebytes263+=n313;dmabytes263+=n313;ordinary263++;
 end endtask
 task ordinary_task263;''')
    s=once(s,'   else if(dut.flow.state==dut.flow.DMA&&staged)begin', '''   else if(dut.flow.state==dut.flow.DMA&&staged&&dut.flow.owner==dut.flow.TILE)tile_consumer313();
   else if(dut.flow.state==dut.flow.DMA&&staged)begin''')
    return s
