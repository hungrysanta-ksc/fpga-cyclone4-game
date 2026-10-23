# SPDX-License-Identifier: MIT
"""One snapshot read selector and host-owned record load/credit path."""
from nes_delta231 import once


def apply(d):
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'reg [199:0] snapshot;', 'reg [7:0] reply_byte315;\n reg [199:0] snapshot;')
    s=once(s,"wire [7:0] crc_byte=request_step?incoming:snapshot[199-crc_at*8-:8];",'''wire [4:0] snapshot_at315=byte_event?count[4:0]:crc_at;
 wire [7:0] snapshot_byte315=snapshot[199-snapshot_at315*8-:8];
 wire [7:0] crc_byte=request_step?incoming:snapshot_byte315;''')
    s=once(s,"wire [7:0] reply=count==status_length?status_crc:\n  (count>=1&&count<status_length)?snapshot[199-(count-1)*8-:8]:8'd0;", 'wire [7:0] reply=reply_byte315;')
    s=once(s,'status_length<=0;crc_at<=0;crc_busy<=0;', 'status_length<=0;crc_at<=0;crc_busy<=0;reply_byte315<=0;')
    s=once(s,'else if(crc_busy)begin', 'else if(crc_busy&&!byte_event)begin')
    s=once(s,'if(ss[1])begin bits<=0;', 'if(ss[1])begin reply_byte315<=0;bits<=0;')
    s=once(s,'if(bits==7)begin', '''if(bits==7)begin
     if(count!=0)begin
      if(count+1==status_length)reply_byte315<=status_crc;
      else if(count+1<status_length)reply_byte315<=snapshot_byte315;
      else reply_byte315<=0;
     end''')
    s=once(s,"begin snapshot<={source_status[183:0],16'd0};", "begin reply_byte315<=source_status[183:176];snapshot<={source_status[183:0],16'd0};")
    s=once(s,"8'he0:begin snapshot<=", "8'he0:begin reply_byte315<=output_status[183:176];snapshot<=")
    s=once(s,"snapshot<={8'hfb,output_status[175:128]", "reply_byte315<=8'hfb;snapshot<={8'hfb,output_status[175:128]")
    s=once(s,'default:begin snapshot<=0;', 'default:begin reply_byte315<=0;snapshot<=0;')
    p.write_text(s,newline='\n')

    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'input wire load_enable312,', 'input wire load_enable312,input wire [3:0] load_at315,')
    s=once(s,'reg bad_header312,loaded312,loading312;\n reg [4:0] load_at312,clear_at312;\n reg clearing312,mirror312;\n reg [4:0] mirror_at312;reg [7:0] mirror_data312;', 'reg bad_header312;')
    s=once(s,'wire full=used==2;', "wire empty315=accepted[1:0]==retired[1:0];\n wire full=accepted[1:0]==(retired[1:0]^2'b10);")
    s=s.replace('loading312?read_base312+{5\'d0,load_at312}', "load_enable312?read_base312+{6'd0,load_at315}")
    s=once(s,'assign record_valid312=loading312&&load_at312!=0&&!reset&&!fault;', 'assign record_valid312=load_enable312&&load_at315!=0&&!reset&&!fault;')
    s=once(s,"assign record_at312=load_at312-1'b1;", "assign record_at312={1'b0,load_at315}-1'b1;")
    s=once(s,'assign storage_empty312=used==0;', 'assign storage_empty312=empty315;')
    s=once(s,'assign packet_ready=used!=0&&loaded312&&enable&&!reset&&!fault;', 'assign packet_ready=!empty315&&enable&&!reset&&!fault;')
    a=s.index('   if(clearing312)begin');b=s.index('if(!ss[1]&&sck[1]',a)
    s=s[:a]+'   '+s[b:]
    s=once(s,'(used!=0)};', '(!empty315)};')
    s=once(s,'loaded312<=0;loading312<=0;load_at312<=0;ingress_length312<=0;', 'ingress_length312<=0;')
    s=once(s,'   clearing312<=0;clear_at312<=0;mirror312<=0;mirror_at312<=0;mirror_data312<=0;','')
    a=s.index('   if(!fault&&enable)begin');b=s.index('   if(consume_record312',a)
    s=s[:a]+s[b:]
    s=once(s,"retired<=retired+1'b1;loaded312<=0;loading312<=0;", "retired<=retired+1'b1;")
    s=once(s,'||clearing312||mirror312','')
    s=once(s,"      if(incoming==8'he1&&enable&&!full&&!fault)begin clearing312<=1;clear_at312<=0;end",'')
    s=once(s,'if(clearing312||mirror312)fault<=1;\n       else if(byte_count<=16)begin','if(byte_count<=16)begin')
    assert not any(x in s for x in ('clearing312','load_at312','loaded312','loading312','mirror312'))
    p.write_text(s,newline='\n')

    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'localparam TILEWAIT313=54;', 'localparam TILEWAIT313=54,HLOAD315=55,HCHECK315=56;')
    s=once(s,'.load_enable312(state==IDLE&&!qretire)', '.load_enable312(state==HLOAD315),.load_at315(at[3:0])')
    s=once(s,'if(state!=IDLE)failed<=1;', 'if(state!=HLOAD315)failed<=1;')
    s=once(s,'0:active305.op<=record_byte312;1:active305.section<=record_byte312;', '''0:begin active305.op<=record_byte312;active305.token<=0;active305.left<=0;end
     1:active305.section<=record_byte312;''')
    s=once(s,'qlen<=queue_length312;at<=0;\n       state<=CHECK;', 'at<=0;state<=HLOAD315;')
    s=once(s,'     CHECK:begin', '''     HLOAD315:begin
      if(at==(header[0]==14?15:header[0]==12?14:10))state<=HCHECK315;
      else at<=at+1'b1;
     end
     HCHECK315:begin qlen<=queue_length312;at<=0;state<=CHECK;end
     CHECK:begin''')
    p.write_text(s,newline='\n')


def observe(s):
    return s.replace('dut.flow.queue.loaded312','(dut.flow.state!=dut.flow.HLOAD315)').replace('dut.flow.queue.loading312','dut.flow.queue.load_enable312').replace('dut.flow.queue.load_at312','dut.flow.queue.load_at315')
