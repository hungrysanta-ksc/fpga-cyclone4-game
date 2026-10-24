# SPDX-License-Identifier: MIT
"""Ordinary data commands share staging and the receipt completion path.

BEGIN and tile command admission still use the legacy view in this candidate.
"""
from nes_delta231 import once


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'wire [11:0] length=active305.span[11:0],first=',
           'wire [11:0] length=(active305.op==2||active305.op==4||active305.op==5||active305.op==8)?active305.encoded[11:0]:active305.span[11:0],first=')
    s=once(s,'(state==XWAIT298&&range_ready&&(data_command278||header[0]==7))', '(state==XWAIT298&&range_ready&&header[0]==7)')
    s=once(s,'assign ordinary_ready=state==NORMAL&&qr&&!fault&&!rst&&!invalidate_banks;',
           '')
    s=once(s,'wire [11:0] chunk_length;wire [31:0] chunk_token;', '''wire [11:0] chunk_length;wire [31:0] chunk_token;
 assign ordinary_ready=((state==NORMAL&&qr)||(state==DMA&&data_command278&&chunk_ready))&&!fault&&!rst&&!invalidate_banks;''')
    # Ordinary consumes have their own endpoint and monotonic namespace.
    # STOP cannot reset the counter; only board reset with bus quiescence can.
    s=once(s,'reg [31:0] allocation,last_serial;', 'reg [31:0] allocation,last_serial,ordinary_next313;')
    s=once(s,'wire allocate;', 'wire allocate,ordinary_allocate313;')
    s=once(s,'allocation<=INITIAL_TOKEN;last_serial<=0;', 'allocation<=INITIAL_TOKEN;last_serial<=0;ordinary_next313<=1;')
    s=once(s,'if(!rst&&allocate&&allocation!=32\'hffffffff)', '''if(!rst&&ordinary_allocate313&&ordinary_next313!=32'hffffffff)
    ordinary_next313<=ordinary_next313+1'b1;
   if(!rst&&allocate&&allocation!=32'hffffffff)''')
    s=once(s,'wire mbeg=state==OPEN&&owner==MAP&&!failed&&token==allocation&&allocation!=32\'hffffffff;',
           "wire mbeg=state==OPEN&&owner==MAP&&!failed&&(data_command278||(token==allocation&&allocation!=32'hffffffff));")
    s=once(s,'assign allocate=begin_ready&&((owner==TILE&&tbeg)||(owner==MAP&&mbeg));',
           'assign ordinary_allocate313=state==OPEN&&data_command278&&owner==MAP&&begin_ready;\n assign allocate=begin_ready&&((owner==TILE&&tbeg)||(owner==MAP&&mbeg&&!data_command278));')
    s=s.replace('.begin_token(allocation)', '.begin_token(owner==MAP&&data_command278?token:allocation)')
    s=once(s,'wire receipt_valid282=(state==OTILE||state==OSELECT)&&',
           'wire receipt_valid282=(state==OTILE||state==OSELECT||(state==SEND&&data_command278))&&')
    s=once(s,'assign range_valid=state==SEND&&range_ready&&!rst;',
           'assign range_valid=state==SEND&&!data_command278&&range_ready&&!rst;')
    # CRC observes real staging bus reads; the independent actual receipt is
    # committed only after complete coverage and the four-byte consume token.
    s=once(s,"wire [15:0] tap_address278=startpos+{8'd0,address[7:0]}-16'd16;",
           "wire [15:0] tap_address278=startpos+{8'd0,address[7:0]};")
    s=once(s,'wire tap_capture278=state==NORMAL', 'wire tap_capture278=state==DMA&&data_command278')
    s=once(s,"address[23:8]==16'h4000&&address[7:0]>=16;", "address[23:8]==16'h4008;")
    s=once(s,'if(address[7:0]<20)pattern278[(address[1:0])*8+:8]<=qdata;',
           'if(address[7:0]<4)pattern278[(address[1:0])*8+:8]<=aperture_data;')
    s=once(s,'tap_value278<=qdata;', 'tap_value278<=aperture_data;')
    s=once(s,"{8'd0,address[7:0]}==16+plen-1", "{8'd0,address[7:0]}==plen-1")
    # Preserve tile packet token capture until its admission adapter is removed.
    s=once(s,'   if(tap_capture278)begin', '''   if(state==NORMAL&&header[0]==7&&!tap_seen278&&!read_n&&write_n&&bus_valid&&
      address[23:8]==16'h4000&&address[7:0]>=16&&address[7:0]<20)begin
    tap_seen278<=1;pattern278[address[1:0]*8+:8]<=qdata;
   end
   if(tap_capture278)begin''')
    s=once(s,"8'h54:control=state==DPRESENT;", '''8'h60:control=header[0];8'h61:control=header[1];
   8'h62:control=startpos[7:0];8'h63:control=startpos[15:8];
   8'h64:control=plen[7:0];8'h65:control=plen[15:8];
   8'h66:control=active305.span[7:0];8'h67:control=active305.span[15:8];
   8'h68:control={7'd0,identity[48]};
   8'h54:control=state==DPRESENT;''')
    s=once(s,'else if(owner==MAP)state<=SEND;', 'else if(owner==MAP)state<=data_command278?WAIT_RECEIPT:SEND;')
    s=once(s,"wire consume_write=!invalidate_banks&&write_end&&ap==24'h006050;",
           "wire consume_write=!invalidate_banks&&write_end&&ap==(data_command278?24'h006059:24'h006050);")
    s=once(s,'if(consume_write)begin', '''if((ap==24'h006050&&data_command278)||(ap==24'h006059&&!data_command278))failed<=1;
     if(consume_write)begin''')
    s=once(s,'     SEND:if(mready)', '     WAIT_RECEIPT:if(tap_idle278&&range_ready)state<=SEND;\n     SEND:if(mready)')
    target='else begin ordinary_reads<=0;tile_proven<=0;at<=0;state<=NORMAL;end'
    assert s.count(target)==2
    i=s.rindex(target)
    s=s[:i]+'''else if(data_command278)begin
        batch<=0;active305.token<=ordinary_next313;state<=OPEN;
       end else begin ordinary_reads<=0;tile_proven<=0;at<=0;state<=NORMAL;end'''+s[i+len(target):]
    s=once(s,"if(token!=allocation||allocation==32'hffffffff)failed<=1;", "if(data_command278?(ordinary_next313==32'hffffffff||token!=ordinary_next313):(token!=allocation||allocation==32'hffffffff))failed<=1;")
    s=once(s,'if(!batch)parser_address<=20;', 'if(!batch)parser_address<=data_command278?16:20;')
    s=once(s,'last_map_token<=token;map_receipt<=1;', 'if(!data_command278)begin last_map_token<=token;map_receipt<=1;end')
    s=once(s,'if(header[0]==12||header[0]==14)state<=CONSUME;', 'if(header[0]==12||header[0]==14||data_command278)state<=CONSUME;')
    p.write_text(s,newline='\n')


def observe(s):
    s=once(s,'if(dut.flow.state==dut.flow.ACKWAIT&&dut.flow.qdone)begin', '''if((dut.flow.state==dut.flow.ACKWAIT&&dut.flow.qdone)||
     (dut.flow.consume_write&&dut.flow.good_consume&&dut.flow.data_command278))begin''')
    # Only the reference C consumer receives a reconstructed wire envelope;
    # these are zero-time scoreboard calls, never accesses by the SNES CPU.
    s=once(s,'start267=$realtime;read267=0;executed267=0;n267=dut.flow.qlen;head267=dut.flow.queue.retired;', '''start267=$realtime;read267=0;executed267=0;n267=dut.flow.qlen;head267=dut.flow.queue.consumed312;
  for(integer i=0;i<16;i++)begin
   if(i>=4&&i<=9)byte267=i<8?dut.flow.identity[(i-4)*8+:8]:dut.flow.identity[32+(i-8)*8+:8];
   else if(i==2)byte267=dut.flow.packet_seq[7:0]-1'b1;
   else if(i==3)byte267=(dut.flow.packet_seq-1)>>8;
   else byte267=dut.flow.header[i];
   ignore267=call263(1,i,byte267);
  end''')
    s=once(s,'event267=cpu267[cpu_at267];cpu_at267++;', '''event267=cpu267[cpu_at267];cpu_at267++;
   if(event267[31:8]>=24'h006048&&event267[31:8]<=24'h00604f)
    event267[7:0]=dut.flow.chunk_token[event267[9:8]*8+:8];''')
    s=once(s,'if(read267!=n267)$fatal', 'if(read267!=n267-16)$fatal')
    s=once(s,"if(bus_address>=24'h400000&&bus_address<=24'h4000ff)begin ignore267=call263(1,read267,byte267);read267++;end",
           "if(bus_address>=24'h400800&&bus_address<=24'h4008ff)begin ignore267=call263(1,16+read267,byte267);read267++;end")
    s=once(s,'wait(dut.flow.queue.retired!=head267);ordinary263++;cpu_cases267++;',
           'wait(dut.flow.queue.consumed312!=head267);ordinary263++;cpu_cases267++;')
    return s
