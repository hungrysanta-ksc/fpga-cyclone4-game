# SPDX-License-Identifier: MIT
"""Constant-space ARM scans and shared host/NES execution state ownership."""
import re
from nes_delta231 import once
from nes_execute332 import native as previous_native


def native(d):
    previous_native(d)
    p=d/'nes_output264.c';s=p.read_text()
    a=s.index('static unsigned crc16(');b=s.index('\n',a)
    s=s[:a]+'''static unsigned crc16(unsigned c,unsigned b){
 static const uint16_t nibble334[16]={0x0000,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,
  0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 c^=b<<8;c=((c<<4)^nibble334[(c>>12)&15])&65535;
 return ((c<<4)^nibble334[c>>12])&65535;
}'''+s[b:]
    p.write_text(s,newline='\n')
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,' for(unsigned i=1;i<end;i++)if(repeat_bytes(b+i,n-i)>=64)return i;', ''' /* Earliest64-byte period-two run, identical to the old repeated probes.
  * Each input byte is inspected once. Full leading runs retain their length. */
 unsigned equal=2;
 for(unsigned i=2;i<n&&i<end+63;i++){
  equal=b[i]==b[i-2]?equal+1:2;
  if(equal>=64)return i-63;
 }''')
    p.write_text(s,newline='\n')


def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    # One synchronous queue reader for payload and expected storage.
    a=s.index('     MCAP313:begin');b=s.index('     MISSUE313:',a)
    metadata=s[a:b].removeprefix('     MCAP313:begin\n').removesuffix('     end\n')
    s=s[:a]+s[b:]
    s=once(s,'     MREAD313:if(header[0]!=3)state<=MCAP313;else if(range_ready)state<=MSEALWAIT313;\n','')
    s=once(s,'MREAD313=42,MCAP313=43,','MREAD313=PREAD,MCAP313=PCAP,')
    s=once(s,' wire metadata313=(', ' wire metadata313=(header[0]==15||header[0]==10||header[0]==11||header[0]==3)&&(')
    s=once(s,'     PREAD:state<=PCAP;', '     PREAD:if(header[0]!=3)state<=PCAP;else if(range_ready)state<=MSEALWAIT313;')
    s=once(s,'     PCAP:begin\n      if(header[0]==1)', '     PCAP:begin\n      if(metadata313)begin\n'+metadata+'      end else if(header[0]==1)')
    # The validator directly accepts from the DMA/tap drain state. Commit the
    # ordered receipt and release the aperture on its completed RAM walk.
    s=s.replace('SEND=11,','').replace('CONSUME=13,','')
    s=s.replace('state==SEND','(state==WAIT_RECEIPT&&tap_idle278)')
    s=s.replace('state==CONSUME','(state==XWAIT298&&range_ready)')
    s=s.replace('state<=data_command278?WAIT_RECEIPT:SEND;', 'state<=WAIT_RECEIPT;').replace('state<=SEND;','state<=WAIT_RECEIPT;')
    s=once(s,'     WAIT_RECEIPT:if(tap_idle278&&range_ready)state<=WAIT_RECEIPT;\n     SEND:if(mready)state<=XWAIT298;',
        '     WAIT_RECEIPT:if(tap_idle278&&range_ready)state<=XWAIT298;')
    a=s.index('     CONSUME:begin');b=s.index('     PREWAIT:',a)
    completion=s[a:b].removeprefix('     CONSUME:begin\n').removesuffix('     end\n')
    s=s[:a]+s[b:]
    s=once(s,'      if(header[0]==12||header[0]==14||header[0]==7||data_command278)state<=CONSUME;',
        '      if(header[0]==12||header[0]==14||header[0]==7||data_command278)begin\n'+completion+'      end')
    p.write_text(s,newline='\n')

    # Record-open and end-record flush are already held by the source FSM.
    p=d/'nes_core257.sv';s=p.read_text()
    s=once(s,'module nes_core257(', 'module nes_core257(output wire record_active334,output reg [2:0] plan_state334,input wire [2:0] plan_next334,')
    s=once(s,' assign record_last319=', ' assign record_active334=state==SREAD||state==SBYTE;\n assign record_last319=')
    s=once(s,' assign output_phase=state==V_IDLE;', ''' reg output_mode334;
 assign output_phase=output_mode334;
 always @*begin
  plan_state334=0;
  if(output_mode334)case(state)
   V_IDLE:plan_state334=0;SREAD:plan_state334=1;SBYTE:plan_state334=2;
   BLOCKEND:plan_state334=3;REQUEST:plan_state334=4;FETCH:plan_state334=5;ENDTRAILER:plan_state334=6;
   default:plan_state334=0;
  endcase
 end''')
    # Plan reads reuse the same state register after source retirement, never
    # the source write enables, query prefetch, or cross-clock mailboxes.
    s=once(s,'assign record_active334=state==SREAD||state==SBYTE;', 'assign record_active334=!output_mode334&&(state==SREAD||state==SBYTE);')
    s=once(s,'   state<=IDLE;external_range', '   output_mode334<=0;state<=IDLE;external_range')
    s=once(s,'else if(!fault&&v_display_ack&&state!=V_IDLE)', 'else if(!fault&&v_display_ack&&(!output_mode334||state!=V_IDLE))')
    s=once(s,'    case(state)\n    IDLE:', '''    if(output_mode334)begin
     if(plan_zero319)cursor<=0;else if(plan_step319)cursor<=cursor+13'd1;
     case(plan_next334)
      0:state<=V_IDLE;1:state<=SREAD;2:state<=SBYTE;3:state<=BLOCKEND;
      4:state<=REQUEST;5:state<=FETCH;6:state<=ENDTRAILER;
      default:begin fault<=6;base_valid<=0;end
     endcase
     if(v_display_ack)begin output_mode334<=0;state<=IDLE;end
    end else case(state)
    IDLE:''')
    s=once(s,'done<=1;rec_i<=0;', 'done<=1;output_mode334<=1;rec_i<=0;')
    a=s.index('    V_IDLE:begin\n');b=s.index('    default:',a);s=s[:a]+s[b:]
    # All source writes, including a pending second mask port, remain disabled
    # in plan phase. Source CRC pending is drained by ack_ready before entry.
    s=once(s,'assign ram_a_we=', 'assign ram_a_we=!output_mode334&&')
    p.write_text(s,newline='\n')
    p=d/'nes_transport257.sv';s=p.read_text()
    s=once(s,'module nes_transport257(', 'module nes_transport257(input wire record_active334,')
    s=once(s,'reg sfault,hfault,bank,flush_record;','reg sfault,hfault,bank;')
    s=once(s,'reg [7:0] used;reg record_open319;', 'reg [7:0] used;wire record_open319=record_active334;')
    s=s.replace('record_open319<=0;','').replace('flush_record<=0;','')
    s=once(s,'else begin record_open319<=1;flush_record<=record_flush;end','else begin end')
    s=once(s,'if(record_last319)used<=used+1\'b1;', 'used<=used+1\'b1;')
    s=once(s,'(flush_record||used==248)', '(record_flush||used==248)')
    p.write_text(s,newline='\n')

    p=d/'nes_plan_batch206.sv';s=p.read_text()
    s=once(s,'module nes_plan_batch206', 'module nes_plan_batch206') # parameterized ports below
    s=once(s,' input wire [9:0] plan_cursor319,', ' input wire [2:0] plan_state334,output reg [2:0] plan_next334,\n input wire [9:0] plan_cursor319,')
    s=once(s,' reg [2:0] state;', ' wire [2:0] state=plan_state334;')
    s=re.sub(r'state<=\w+;', 'begin end ', s)
    s=once(s,' integer i;\n always @(posedge nes_clk', ''' always @*begin
  plan_next334=state;
  if(!nr&&!nc)case(state)
   WAIT:if(word_valid)plan_next334=READ;
   READ:if(read_cursor314<batch_length&&remaining!=0&&remaining<=16&&!(at>=16&&alt_index>=8)&&
       !(at>=16&&!plan_alt_mask[alt_index]))plan_next334=CAPTURE;
   CAPTURE:plan_next334=at==length-1?CHECK:READ;
   CHECK:if(shape_ok&&lease_ok&&!(bg_closed295&&(partial295||plan_kind==0||plan_kind==2)))
    plan_next334=plan_kind==3?ENDING:READY;
   READY:if(plan_valid&&plan_ready)plan_next334=RUN;
   RUN:if(tile_done)plan_next334=remaining==1?WAIT:READ;
   ENDING:if(end_valid&&end_ready)plan_next334=WAIT;
   default:plan_next334=WAIT;
  endcase
 end
 integer i;
 always @(posedge nes_clk''')
    # Conditional assignment expressions need explicit removal as well.
    s=once(s,'else state<=plan_kind==3?ENDING:READY;', 'else begin end')
    p.write_text(s,newline='\n')
    ports='output wire [2:0] plan_state334,input wire [2:0] plan_next334,'
    conn='.plan_state334(plan_state334),.plan_next334(plan_next334),'
    for name,module,inst in [('nes_joint257.sv','nes_joint257','nes_core257 encoder('),('nes_joint266.sv','nes_joint266','nes_joint257 core(')]:
        p=d/name;s=p.read_text()
        actual_module='nes_joint267_board' if 'module nes_joint267_board ' in s else module
        marker='module '+module+'(' if name=='nes_joint257.sv' else 'module '+actual_module+' #(parameter SHARED=1)('
        s=once(s,marker,marker+ports)
        s=once(s,inst,inst+conn)
        if name=='nes_joint257.sv':
            s=once(s,'wire record_last319;', 'wire record_last319,record_active334;')
            s=once(s,'nes_core257 encoder(', 'nes_core257 encoder(.record_active334(record_active334),')
            s=once(s,'nes_transport257 transport(', 'nes_transport257 transport(.record_active334(record_active334),')
        p.write_text(s,newline='\n')
    for name in ('nes_plan_path267.sv','nes_plan_rom267.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'input wire [9:0] plan_cursor319,', 'input wire [2:0] plan_state334,output wire [2:0] plan_next334,input wire [9:0] plan_cursor319,')
        s=once(s,' transport(.plan_cursor319', ' transport('+conn+'.plan_cursor319')
        p.write_text(s,newline='\n')
    for name,instances in [('nes_live_joint.sv',('native_joint267','retained_plan267')),('joint266_tb.sv',('dut','planrom'))]:
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'wire [113:0] link270;', 'wire [2:0] plan_state334,plan_next334;\nwire [113:0] link270;')
        for inst in instances:
            # Other generations may prepend ports before link270.
            s=once(s,inst+'(',inst+'('+conn)
        p.write_text(s,newline='\n')
