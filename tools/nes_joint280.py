# SPDX-License-Identifier: MIT
"""N5-v2 raw MASK/base reuse and common checked SPI request fields.

The raw cache follows input serial, never a display bank. STOP invalidates it.
The common request context exists only while SS is low; endpoint lifetimes,
CRC/coverage, source commit, plan retire and output ACK remain separate.
"""
from nes_delta231 import once
from nes_joint278 import patch as previous
from nes_delta231 import ROOT


def source(s):
    s=once(s,'base_hi[0:511]','base_hi[0:1023]')
    s=s.replace('base_hi[base_addr[8:0]]','base_hi[base_addr[9:0]]')
    s=once(s,'reg [12:0] cursor,raw_at,raw_limit;','reg [12:0] cursor,raw_limit;\n reg raw_cold;')
    s=s.replace('build_i,raw_count','build_i')
    s=s.replace('GEOTRAILER,RAWSTART,RAWASK,RAWWAIT,RAWCHECK,ENDTRAILER',
                'GEOTRAILER,RAWSTART,ENDTRAILER')
    s=once(s,'{H,MASK,SHIFT,GEO,RAW,ENDREC}','{H,MASK,SHIFT,GEO,ENDREC}')
    s=once(s,'&&!raw_mode&&state!=IDLE&&q_cursor<4385&&q_cursor!=4320',
        '&&state!=IDLE&&((!raw_mode&&q_cursor<4385&&q_cursor!=4320)||(raw_mode&&q_cursor<4398+raw_limit))')
    s=once(s,'wire q_synthetic=cursor==4320||cursor>=4385;',
        'wire q_synthetic=!raw_mode&&(cursor==4320||cursor>=4385);')
    s=once(s,'if(q_cursor<2112)begin',
        "if(raw_mode)begin q_section=7;q_index=q_cursor-13'd4398;q_active=1;end\n  else if(q_cursor<2112)begin")
    s=once(s,'assign in_valid=live&&state==FETCH&&(q_have||q_synthetic);',
        'assign in_valid=live&&state==FETCH&&(q_have||q_synthetic);')
    s=once(s,'assign in_ready=in_valid;assign raw_query=live&&state==RAWASK;assign raw_index=cursor;',
        "assign in_ready=in_valid;assign raw_query=1'b0;assign raw_index=0;")
    s=once(s,'wire changed=cold||base_q!=new_byte;',
        'wire changed=(raw_mode?raw_cold:cold)||base_q!=new_byte;')
    s=once(s,'2:header_byte=1;','2:header_byte=2;')
    s=once(s,"3:header_byte={7'd0,cold};","3:header_byte={6'd0,raw_cold,cold};")
    s=s.replace("  if(kind==RAW)a_addr={1'b0,rec_i}-9'd3;\n",'')
    s=s.replace("   RAWWAIT:begin a_addr={1'b0,raw_count};a_we=raw_response&&raw_hit&&raw_data[63:6]==0;a_w=raw_data[7:0];end\n",'')
    a=s.index('  if(kind==RAW)case(rec_i)');b=s.index('  if(kind==GEO',a);s=s[:a]+s[b:]
    s=once(s,'if(cursor==4398)begin build_i<=0;state<=GEOTRAILER;end',
        '''if(raw_mode&&cursor==4398+raw_limit)begin build_i<=0;state<=ENDTRAILER;end
   else if(!raw_mode&&cursor==4398)begin build_i<=0;state<=GEOTRAILER;end''')
    s=s.replace('raw_at<=0;','').replace('raw_count<=0;','')
    s=once(s,'base_valid<=0;cold<=1;','base_valid<=0;cold<=1;raw_cold<=1;')
    s=once(s,'(q_section==5&&raw_data[63:6]!=0)',
        '((q_section==5||q_section==7)&&raw_data[63:6]!=0)')
    s=once(s,'cold<=!base_valid;raw_limit<=',
        'cold<=!base_valid;raw_cold<=!base_valid||patch_count!=admitted_raw;raw_limit<=')
    s=once(s,'if(row_count!=224||','if(patch_count>2||row_count!=224||')
    s=once(s,'if(cursor>=4398||(cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))',
        'if(cursor>=4398+raw_limit||(!raw_mode&&cursor>=4398)||(!raw_mode&&cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))')
    s=once(s,"spans<=spans+1'b1;expanded<=expanded+(shift_ok?16'd66:{9'd0,diff_count});",
        "if(!raw_mode)begin spans<=spans+1'b1;expanded<=expanded+(shift_ok?16'd66:{9'd0,diff_count});end")
    s=s.replace('      RAW:begin raw_at<=cursor;raw_count<=0;if(cursor==raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=RAWASK;end\n','')
    # raw_count reset removed above; remove the resulting legacy branch too.
    s=s.replace('      RAW:begin raw_at<=cursor;if(cursor==raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=RAWASK;end\n','')
    a=s.index('    RAWSTART:');b=s.index('    ENDTRAILER:',a)
    s=s[:a]+'''    RAWSTART:begin
     raw_mode<=1;cursor<=4398;block_id<=68;row_i<=0;row_size<=64;mask_bytes<=8;
     diff_count<=0;mask_acc<=0;q_have<=0;q_pending<=0;
     if(!raw_limit)begin build_i<=0;state<=ENDTRAILER;end else state<=FETCH;
    end
'''+s[b:]
    return s


def patch(d):
    previous(d)
    apply(d)


def apply(d):
    p=d/'nes_core257.sv';p.write_text(source(p.read_text()),encoding='utf-8',newline='\n')
    # One transaction context is valid only until SS rises. All host users use
    # the same wires; no CDC or outstanding endpoint state is merged.
    for p in d.glob('*.sv'):
        if p.name.endswith('_tb.sv'):continue
        s=p.read_text().replace('[48:0] link270','[106:0] link270')
        s=s.replace('=link270;','=link270[48:0];')
        p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'assign link={request_crc', 'assign link[48:0]={request_crc')
    s=s.replace('[48:0] link);','[106:0] link);')
    s=once(s,' always @(posedge clk or posedge reset)begin',
        (ROOT/'tools/nes_exchange280.inc').read_text()+'\n always @(posedge clk or posedge reset)begin')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_plan_spi200.sv';s=p.read_text()
    s=once(s,'reg [15:0] length;reg [7:0] number,tail,received8;wire [7:0] request8=common_crc270;',
        'wire [15:0] length=link270[106:91];wire [7:0] number=link270[74:67];')
    s=once(s,'reg [15:0] received16,accepted;reg [7:0] reply;',
        'wire [15:0] received16=link270[90:75];reg [15:0] accepted;reg [7:0] reply;')
    s=s.replace('length<=0;number<=0;tail<=0;received8<=0;received16<=0;','')
    s=s.replace('length<=0;number<=0;received16<=0;received8<=0;tail<=0;','')
    s=s.replace("received8!=request8||tail!=8'ha5","!link270[66]||!link270[65]")
    a=s.index("     end else if(command==8'hea)begin");b=s.index('      end else if(count<=length+3)',a)
    s=s[:a]+'''     end else if(command==8'he9)begin
      if(count==3)begin
       if(length<3||length>512||incoming==0||incoming>16)fault<=1;
'''+s[b:]
    s=s.replace('end else if(count<=length+3)', 'end else if(count>=4&&count<=length+3)')
    a=s.index('      end else if(count==length+4)');b=s.index('\n     end',a)
    s=s[:a]+'      end'+s[b:]
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text()
    a=s.index(' function automatic [15:0] crc16');b=s.index(' wire [7:0] common_crc270',a);s=s[:a]+s[b:]
    s=s.replace('reg [15:0] request_crc;','wire [15:0] request_crc=link270[64:49];')
    s=s.replace("   request_crc<=16'hffff;",'').replace("request_crc<=16'hffff;",'')
    s=s.replace("      request_crc<=crc16(16'hffff,incoming);",'')
    s=s.replace('      request_crc<=crc16(request_crc,incoming);','')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_transport257.sv';s=p.read_text()
    s=once(s,'input wire src_clk,host_clk,reset,abort_source,',
        'input wire [15:0] frame_generation,\n input wire src_clk,host_clk,reset,abort_source,')
    s=s.replace('[23:0] descriptor0,descriptor1','[39:0] descriptor0,descriptor1')
    s=s.replace('[23:0] block0,block1','[39:0] block0,block1').replace('.WIDTH(24)','.WIDTH(40)')
    s=s.replace('<={length,checksum}','<={frame_generation,length,checksum}')
    a=s.index(' reg read_bank,read_seen,reading;')
    s=s[:a]+(ROOT/'tools/nes_source_exchange280.inc').read_text()+'\nendmodule\n'
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text().replace('transport(.link270',
        'transport(.frame_generation(frame_generation),.link270')
    p.write_text(s,encoding='utf-8',newline='\n')
