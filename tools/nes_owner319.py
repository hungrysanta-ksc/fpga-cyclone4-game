# SPDX-License-Identifier: MIT
"""315: clock-local transaction admission and source/plan cursor ownership.

Physical RAM ports and independent validator remain unchanged. The source
encoder owns record termination; transport owns sealed-bank publication.
"""
from nes_delta231 import once

def apply(d):
    # Host SPI transaction owner samples the destination at command acceptance.
    # Endpoints still enforce current enable/fault and exact framing at seal.
    for p in d.glob('*.sv'):
        s=p.read_text();s=s.replace('[112:0] link270','[113:0] link270')
        p.write_text(s,newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'output wire [112:0] link);','input wire queue_admit319,plan_admit319,output wire [113:0] link);')
    s=once(s,'reg reply_bit282;', '''reg transaction_admit319;
 assign link[113]=transaction_admit319;
 always @(posedge clk or posedge reset)begin
  if(reset)transaction_admit319<=0;
  else if(ss[1])transaction_admit319<=0;
  else if(byte_event&&count==0)transaction_admit319<=
   incoming==8'he1 ? queue_admit319 : incoming==8'he9 ? plan_admit319 : 1'b0;
 end
 reg reply_bit282;''');p.write_text(s,newline='\n')
    for n,regtext,resettext,settext,ready in [
      ('nes_queue260.sv','reg can_write;','can_write<=0;','can_write<=enable&&!full&&!fault;','enable&&!full&&!fault'),
      ('nes_plan_spi200.sv','reg can_write,ended,retiring;','can_write<=0;','can_write<=live&&!ended&&!retiring&&plan_idle&&accepted!=16\'hffff;',"live&&!ended&&!retiring&&plan_idle&&accepted!=16'hffff")]:
        p=d/n;s=p.read_text()
        s=once(s,'input wire [113:0] link270,','output wire admit319,input wire [113:0] link270,')
        replacement='wire can_write=link270[113];'+('reg ended,retiring;' if n.startswith('nes_plan') else '')
        s=once(s,regtext,replacement);s=once(s,resettext,'');s=once(s,settext,'')
        s=once(s,'endmodule',f'assign admit319={ready};\nendmodule');p.write_text(s,newline='\n')
    # Route queue admission to the common host transaction owner.
    p=d/'nes_mux260.sv';s=p.read_text();s=once(s,'output wire exec_start298,','output wire queue_admit319,output wire exec_start298,')
    s=once(s,'nes_queue260 queue(', 'nes_queue260 queue(.admit319(queue_admit319),');p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text();s=once(s,'input wire [113:0] link270,','output wire queue_admit319,input wire [113:0] link270,')
    s=once(s,' flow(', ' flow(.queue_admit319(queue_admit319),');p.write_text(s,newline='\n')
    for name in ('nes_plan_path267.sv','nes_plan_rom267.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'input wire [113:0] link270,','output wire plan_admit319,input wire [113:0] link270,')
        s=once(s,'nes_plan_spi200 endpoint(', 'nes_plan_spi200 endpoint(.admit319(plan_admit319),');p.write_text(s,newline='\n')
    # Source record position is authoritative; remove a duplicate byte countdown.
    p=d/'nes_core257.sv';s=p.read_text();s=once(s,'module nes_core257(', 'module nes_core257(output wire record_last319,')
    s=once(s,'assign byte_data=out_byte;',"assign byte_data=out_byte;\n assign record_last319=rec_i+8'd1==record_length;")
    p.write_text(s,newline='\n')
    p=d/'nes_transport257.sv';s=p.read_text();s=once(s,'module nes_transport257(', 'module nes_transport257(input wire record_last319,')
    s=once(s,'reg [7:0] used,remaining;', 'reg [7:0] used;reg record_open319;')
    s=s.replace('!remaining','!record_open319').replace('remaining!=0','record_open319').replace('remaining==0','!record_open319')
    s=once(s,'remaining<=0;','record_open319<=0;');s=once(s,'remaining<=record_length;','record_open319<=1;')
    s=once(s,"remaining<=remaining-1'b1;",'if(record_last319)record_open319<=0;')
    assert 'remaining' not in s;p.write_text(s,newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text();s=once(s,'nes_core257 encoder(', 'wire record_last319;\nnes_core257 encoder(.record_last319(record_last319),')
    s=once(s,'nes_transport257 transport(', 'nes_transport257 transport(.record_last319(record_last319),');p.write_text(s,newline='\n')
    # One NES cursor changes owner only after the source/input ACK phase.
    ports='input wire plan_zero319,plan_step319,output wire [9:0] plan_cursor319,'
    p=d/'nes_core257.sv';s=p.read_text();s=once(s,'module nes_core257(', 'module nes_core257('+ports)
    s=once(s,'reg [12:0] cursor,raw_limit;','reg [12:0] cursor,raw_limit;\n assign plan_cursor319=cursor[9:0];')
    s=once(s,'state<=V_IDLE;end',"cursor<=0;state<=V_IDLE;end")
    s=once(s,'V_IDLE:if(v_display_ack)state<=IDLE;', '''V_IDLE:begin
     if(plan_zero319)cursor<=0;
     else if(plan_step319)cursor<=cursor+13'd1;
     if(v_display_ack)state<=IDLE;
    end''');p.write_text(s,newline='\n')
    for name,module in [('nes_joint257.sv','nes_joint257'),('nes_joint266.sv',None)]:
        p=d/name;s=p.read_text()
        if module:s=once(s,'module '+module+'(', 'module '+module+'('+ports)
        else:s=once(s,'output wire queue_admit319,',ports+'output wire queue_admit319,')
        target='nes_core257 encoder(' if module else 'nes_joint257 core('
        s=once(s,target,target+'.plan_zero319(plan_zero319),.plan_step319(plan_step319),.plan_cursor319(plan_cursor319),');p.write_text(s,newline='\n')
    p=d/'nes_plan_batch206.sv';s=p.read_text()
    s=once(s,' input wire host_clk,',' input wire [9:0] plan_cursor319,output wire plan_zero319,plan_step319,\n input wire host_clk,')
    s=once(s,'count,batch_length,read_cursor314;', 'count,batch_length;wire [9:0] read_cursor314=plan_cursor319;')
    s=once(s,' integer i;\n always @(posedge nes_clk', ''' assign plan_zero319=!nr&&!nc&&state==WAIT&&word_valid;
 assign plan_step319=!nr&&!nc&&((state==CAPTURE&&at!=length-1)||(state==RUN&&tile_done&&remaining!=1));
 integer i;
 always @(posedge nes_clk''')
    s=s.replace('read_cursor314<=0;','').replace("read_cursor314<=read_cursor314+1'b1;",'').replace("read_cursor314<=read_cursor314+10'd1;",'')
    p.write_text(s,newline='\n')
    for name in ('nes_plan_path267.sv','nes_plan_rom267.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'output wire plan_admit319,','input wire [9:0] plan_cursor319,output wire plan_zero319,plan_step319,output wire plan_admit319,')
        s=once(s,' transport(.host_clk', ' transport(.plan_cursor319(plan_cursor319),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.host_clk');p.write_text(s,newline='\n')
    for name in ('nes_live_joint.sv','joint266_tb.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'wire [113:0] link270;', 'wire queue_admit319,plan_admit319,plan_zero319,plan_step319;wire [9:0] plan_cursor319;\nwire [113:0] link270;')
        s=once(s,'nes_spi270 spi_front270(', 'nes_spi270 spi_front270(.queue_admit319(queue_admit319),.plan_admit319(plan_admit319),')
        for instance in (('native_joint267','retained_plan267') if name=='nes_live_joint.sv' else ('dut','planrom')):
            admission='queue_admit319' if instance in ('native_joint267','dut') else 'plan_admit319'
            s=once(s,instance+'(.link270',instance+f'(.{admission}({admission}),.plan_cursor319(plan_cursor319),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.link270')
        p.write_text(s,newline='\n')
