# SPDX-License-Identifier: MIT
"""Common completion/identity response and rotating SPI response engine."""
import os
from nes_resume330 import native as previous
from nes_delta231 import once


def native(d):
    previous(d)
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'if(map_state330>=2||!metadata_ready317())return 1;',
           'if(map_state330>=2||!metadata_ready317())return 2;')
    s=once(s,'uint8_t *b=map_scratch330();if(!b)return 1;',
           'uint8_t *b=map_scratch330();if(!b)return 2;')
    s=once(s,'if(dirty){if(!map_n330)map_start330=map_w330;map_n330++;map_w330++;}',
           '''if(dirty){
   if(!map_n330)map_start330=map_w330;
   unsigned take=(!(map_w330&7)&&bits[map_w330/8]==255&&map_n330<=24)?8:1;
   map_n330+=take;map_w330+=take;
  }''')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'if(!prepare_map330()){plan_error267=8;return 0;}',
           'unsigned step331=prepare_map330();if(!step331){plan_error267=8;return 0;}if(step331==2)break;')
    p.write_text(s,newline='\n')
    if os.environ.get('NES331_ARM_ONLY')=='1':return
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'unsigned progress282(const uint8_t *p,unsigned n){',
           'static unsigned progress331(const uint8_t *p,unsigned n,unsigned full){')
    s=once(s,'unsigned c=0;for(unsigned i=1;i<13;i++)c=crc8(c,p[i]);',
           'unsigned last=full?24:13;unsigned c=0;for(unsigned i=1;i<last;i++)c=crc8(c,p[i]);')
    s=once(s,'p[13]!=c','p[last]!=c')
    s=once(s,'static unsigned wait_reason302;',
           'unsigned progress282(const uint8_t *p,unsigned n){return progress331(p,n,0);}\nstatic unsigned wait_reason302;')
    a=s.index(' unsigned n=full?26:14;');b=s.index('\n}\nstatic unsigned drain',a)
    s=s[:a]+''' unsigned n=full?25:14;
 if(state259.error)return 0;
 for(unsigned i=0;i<n;i++)status259[i]=0;status259[0]=full?0xe0:0xe2;
 if(!io259(status259,n))return fail(1);
 return full?progress331(status259,n,1):!state259.error;'''+s[b:]
    s=once(s,'state259.token=u32(status259+8);','state259.token=u32(status259+13);')
    s=once(s,'u16(status259+16)!=u16(p+14)||status259[18]!=((state259.bank<<2)|p[1])||u16(status259+19)!=u16(p+10)/(p[1]?32:16)||u16(status259+21)!=generation',
           'u16(status259+17)!=u16(p+14)||status259[19]!=((state259.bank<<2)|p[1])||u16(status259+20)!=u16(p+10)/(p[1]?32:16)||u16(status259+22)!=generation')
    s=once(s,'w32(wire259+17,u32(status259+12))','w32(wire259+17,u32(status259+13))')
    p.write_text(s,newline='\n')
    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'if(command==0xe0)plan_cache282=0;',
           '/* E0 has the same checked progress prefix; status() caches it. */')
    p.write_text(s,newline='\n')


def apply(d):
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,"(command==8'he2 ? 14 : 26)","(command==8'he2 ? 14 : 25)")
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,' assign progress_status={',
           ' wire [31:0] identity_token331=chunk_ready?chunk_token:allocation;\n assign progress_status={')
    s=once(s,'allocation[7:0],allocation[15:8],allocation[23:16],allocation[31:24],\n  chunk_token[7:0],chunk_token[15:8],chunk_token[23:16],chunk_token[31:24],',
           'identity_token331[7:0],identity_token331[15:8],identity_token331[23:16],identity_token331[31:24],32\'d0,')
    p.write_text(s,newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'reg [199:0] snapshot;reg [4:0] status_length,crc_at;reg crc_busy;',
           'reg [199:0] snapshot;reg [4:0] status_length,crc_at;reg crc_busy;\n reg [48:0] progress_key331;\n wire [48:0] live_key331={output_status[175],output_status[151:128],plan_status[167:160],output_status[199:184]};')
    a=s.index(' wire [4:0] snapshot_at315=');b=s.index(' function automatic',a)
    s=s[:a]+''' // CRC and transmission use the same byte lane. Rotate all25 bytes
 // during the pre-response CRC pass, restoring the original byte order.
 wire [7:0] crc_byte=request_step?incoming:snapshot[199:192];
'''+s[b:]
    a=s.index(' assign progress_irq284=');b=s.index(' reg transaction_admit319;',a)
    s=s[:a]+' assign progress_irq284=armed284&&(live_key331!=progress_key331);\n'+s[b:]
    s=once(s,'armed284<=0;progress_mode284<=0;', 'progress_key331<=0;armed284<=0;progress_mode284<=0;')
    s=once(s,'''    status_crc<=crc_next;
    if(crc_at==status_length-2)crc_busy<=0;
    else crc_at<=crc_at+1'b1;''', '''    snapshot<={snapshot[191:0],snapshot[199:192]};
    if(crc_at<status_length-1)status_crc<=crc_next;
    if(crc_at==24)crc_busy<=0;
    else crc_at<=crc_at+1'b1;''')
    s=once(s,'else if(count+1<status_length)reply_byte315<=snapshot_byte315;',
           'else if(count+1<status_length)reply_byte315<=snapshot[191:184];')
    s=once(s,'else reply_byte315<=0;\n     end',
           'else reply_byte315<=0;\n      snapshot<={snapshot[191:0],snapshot[199:192]};\n     end')
    s=once(s,"armed284<=incoming==8'he2", "progress_key331<=live_key331;\n      armed284<=incoming==8'he2")
    s=once(s,"8'he0:begin reply_byte315<=output_status[183:176];snapshot<={output_status[183:8],output_status[199:184],8'd0};status_length<=25;end",
           "8'he0:begin reply_byte315<=8'hfb;snapshot<={8'hfb,output_status[175:128],plan_status[167:144],output_status[199:184],output_status[127:96],output_status[63:8],16'd0};status_length<=24;end")
    p.write_text(s,newline='\n')
