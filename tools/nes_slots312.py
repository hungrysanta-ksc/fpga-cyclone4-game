# SPDX-License-Identifier: MIT
"""Two-slot transport gate. NOT the completed canonical record replacement.

Keep the old execution/checker as a reference while measuring the new credit
and response ABI. A last batch payload can release storage before its actual
DMA receipt. The active descriptor and staging ownership remain held.
"""
from nes_delta231 import once
from nes_ingress307 import native as previous_native


def native(d):
    previous_native(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=s.replace('status259[24]','status259[26]')
    s=once(s,'static unsigned phase_ready302;', '''static unsigned phase_ready302;
static uint16_t issued312,consumed312;
static unsigned consume312(unsigned c){
 unsigned pending=(uint16_t)(issued312-consumed312),delta=(uint16_t)(c-consumed312);
 if(delta>pending)return fail(23);
 consumed312=(uint16_t)c;return 1;
}''')
    s=once(s,'if(n<12)return 1;', 'if(n<14){plan_cache282=0;return 1;}')
    s=once(s,'i<11;i++','i<13;i++')
    s=once(s,'p[1]!=0xfa||p[11]!=c', 'p[1]!=0xfb||p[13]!=c')
    s=once(s,'state259.retired=r;status259[7]=p[7];', 'if(!consume312((p[11]<<8)|p[12]))return 0;\n state259.retired=r;status259[7]=p[7];')
    s=once(s,'unsigned n=full?24:12;', 'unsigned n=full?26:14;')
    s=once(s,'i<24;i++)status259', 'i<26;i++)status259')
    s=once(s,'full?0xf8:0xf9', 'full?0xfc:0xfb')
    s=once(s,'state259.retired=r;return 1;', 'if(!consume312((status259[23]<<8)|status259[24]))return 0;state259.retired=r;return 1;')
    # Credit checks are deliberately changed only in this serializer.
    s=s.replace('pending>4','pending>2').replace('used>4','used>2').replace('used==4','used==2').replace('pending>=4','pending>=2')
    s=s.replace('(uint16_t)(state259.sent-state259.retired)>=4','(uint16_t)(state259.sent-state259.retired)>=2')
    s=s.replace('state259.retired==state259.sent','(state259.retired==state259.sent&&issued312==consumed312)')
    s=once(s,'void reset259(void){','void reset259(void){issued312=consumed312=0;')
    s=once(s,'state259.sent++;state259.sequence++;', '''if(wire259[1]==2||wire259[1]==4||wire259[1]==5||wire259[1]==7||wire259[1]==8||wire259[1]==12||wire259[1]==14)issued312++;
 state259.sent++;state259.sequence++;''')
    # io259 overwrites the wire with its reply, so capture the kind before it.
    s=once(s,'if(!io259(wire259,n+3))return fail(1);', 'unsigned op312=wire259[1];\n if(!io259(wire259,n+3))return fail(1);')
    s=s.replace('if(wire259[1]==2||wire259[1]==4||wire259[1]==5||wire259[1]==7||wire259[1]==8||wire259[1]==12||wire259[1]==14)', 'if(op312==2||op312==4||op312==5||op312==7||op312==8||op312==12||op312==14)')
    p.write_text(s,newline='\n')
    p=d/'nes_bind287.c';s=p.read_text()
    s=once(s,'uint8_t p[12]={0xe2}', 'uint8_t p[14]={0xe2}')
    s=once(s,'io259(p,12)', 'io259(p,14)')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=s.replace('reply267[12]','reply267[14]').replace('i<12;i++)reply267','i<14;i++)reply267')
    s=s.replace('physical267(reply267,12)','physical267(reply267,14)').replace('progress282(reply267,12)','progress282(reply267,14)')
    p.write_text(s,newline='\n')


def apply(d):
    # Preserve existing field bit positions at every endpoint. The new
    # independent consume counter occupies the additional high 16 bits.
    for p in d.glob('*.sv'):
        s=p.read_text().replace('[183:0]','[199:0]')
        p.write_text(s,newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'input wire parser_retire,','input wire parser_retire,input wire consume_record312,')
    s=s.replace('lengths[0:3]','lengths[0:1]').replace('accepted[1:0]','accepted[0]').replace('retired[1:0]','retired[0]')
    s=once(s,'reg [15:0] accepted,retired;', 'reg [15:0] accepted,retired,consumed312;')
    s=once(s,'wire full=used==4;', 'wire full=used==2;')
    # Keep the allocated RAM boundary, reserving canonical manifest space.
    # Raw wire view is retained in this gate and explicitly charged.
    s=once(s,'buffer[{retired[0],read_address}]', "buffer[(retired[0]?10'd752:10'd480)+{2'd0,read_address}]")
    s=once(s,"buffer[{accepted[0],8'd0}+byte_count-1'b1]", "buffer[(accepted[0]?10'd752:10'd480)+byte_count-1'b1]")
    s=once(s,'accepted<=0;retired<=0;fault<=0;', 'accepted<=0;retired<=0;consumed312<=0;fault<=0;')
    s=once(s,'if(parser_retire&&enable&&!fault)begin', "if(consume_record312&&enable&&!fault)consumed312<=consumed312+1'b1;\n   if(parser_retire&&enable&&!fault)begin")
    s=once(s,"command==8'he2 ? 12 : 24", "command==8'he2 ? 14 : 26")
    s=once(s,"{8'hf8,flags,accepted,retired,progress_status,8'd0}", "{consumed312,8'hfc,flags,accepted,retired,progress_status,8'd0}")
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'wire [8:0] qlen;', 'wire [8:0] queue_length312;reg [8:0] qlen;')
    s=once(s,'.packet_length(qlen)', '.packet_length(queue_length312)')
    s=once(s,'.parser_retire(qretire)', '.parser_retire(qretire),.consume_record312(consume_record312)')
    s=once(s,'wire data_command278=', 'assign data_command278=')
    s=once(s,'reg qretire;', '''wire data_command278;
 wire consume_record312=!rst&&!fault&&(
  (state==CONSUME&&(!batch||remaining==1))||
  (state==XWAIT298&&exec_done298&&(data_command278||header[0]==7)));
 reg qretire;''')
    s=once(s,'else if(qr&&have_identity&&!qretire)begin parser_address<=0;', 'else if(qr&&have_identity&&!qretire)begin qlen<=queue_length312;parser_address<=0;')
    s=once(s,'SEAL:state<=batch?DMA:RETIRE;', '''SEAL:begin
      if(batch&&remaining==1)begin qretire<=1;packet_seq<=packet_seq+1'b1;end
      state<=batch?DMA:RETIRE;
     end''')
    s=once(s,'if(batch)begin qretire<=1;packet_seq<=packet_seq+1\'b1;state<=IDLE;end','if(batch)begin state<=IDLE;end')
    p.write_text(s,newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=s.replace('snapshot[183-','snapshot[199-')
    s=once(s,'snapshot<=source_status;','snapshot<={source_status[183:0],16\'d0};')
    s=once(s,'snapshot<=output_status;status_length<=23;', "snapshot<={output_status[183:8],output_status[199:184],8'd0};status_length<=25;")
    s=once(s,"{8'hfa,output_status[175:128],plan_status[167:144],104'd0};status_length<=11;", "{8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],104'd0};status_length<=13;")
    s=once(s,'{output_status[175],output_status[151:128],plan_status[167:160]}', '{output_status[175],output_status[151:128],plan_status[167:160],output_status[199:184]}')
    s=once(s,'{snapshot[175],snapshot[151:128],snapshot[127:120]}', '{snapshot[191],snapshot[167:144],snapshot[143:136],snapshot[119:104]}')
    p.write_text(s,newline='\n')


def observe(s):
    s=once(s,"b=dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i];", '''if(i<16)begin
      if(i>=4&&i<=9)begin
       if(i<8)b=dut.flow.identity[(i-4)*8+:8];else b=dut.flow.identity[32+(i-8)*8+:8];
      end else b=dut.flow.queue.record312[dut.flow.queue.field312(i)*8+:8];
     end else b=dut.flow.queue.buffer[(dut.flow.queue.retired[0]?752:480)+24+i-16];''')
    s=once(s,'dut.exec_busy298&&dut.flow.header[0]!=12&&!dut.flow.qr', 'dut.exec_busy298&&dut.flow.header[0]!=12&&!(dut.flow.header[0]==14&&dut.flow.remaining==1)&&!dut.flow.qr')
    return once(s,' task clear_output;', '''
 reg released312=0;reg [144:0] active312;
 always @(posedge host_clk)begin
  if(reset||!active263||source_fault)released312<=0;
  else begin
   if(dut.flow.qretire&&dut.flow.header[0]==14)begin released312<=1;active312<=dut.flow.active305;end
   if(released312)begin
    if(dut.flow.active305!==active312||dut.flow.mput||dut.flow.owner!=2)
     $fatal(1,"storage release changed unconsumed descriptor/staging owner");
    if(dut.flow.consume_record312)released312<=0;
   end
  end
 end
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.flow.queue.used>2)$fatal(1,"two-slot credit exceeded");
  if(dut.flow.qretire)$fwrite(events261,"release312,%0d,%0d,%0d,%0d,%0t\\n",f,dut.flow.header[0],dut.flow.queue.retired,dut.flow.queue.consumed312,$time);
  if(dut.flow.consume_record312)$fwrite(events261,"receipt312,%0d,%0d,%0d,%0d,%0t\\n",f,dut.flow.header[0],dut.flow.queue.retired,dut.flow.queue.consumed312,$time);
 end
 task clear_output;''')
